import os
import logging
from typing import Dict, Any, List, Optional, Literal
from jinja2 import Environment, FileSystemLoader, Template
from pydantic import BaseModel, Field

logger = logging.getLogger("smart_devtool.generator")

class ParameterModel(BaseModel):
    name: str
    type: str
    location: str = "query"  # path, query, body, header, form, cookie
    required: bool = False
    default: Optional[Any] = None
    description: Optional[str] = ""

class AuthenticationModel(BaseModel):
    type: Literal["bearer_token", "bearer", "api_key_header", "api_key_query", "oauth2", "basic_auth", "jwt", "none"]
    header_name: Optional[str] = ""
    query_parameter: Optional[str] = ""
    scheme: Optional[str] = ""

class EndpointModel(BaseModel):
    name: str
    summary: Optional[str] = ""
    method: str
    path: str
    parameters: List[ParameterModel] = Field(default_factory=list)

class APISchemaModel(BaseModel):
    api_name: str
    base_url: str
    authentication: AuthenticationModel
    environment_variable: Optional[str] = ""
    timeout: int = Field(default=30)
    endpoints: List[EndpointModel] = Field(default_factory=list)

class WrapperGenerator:
    """
    Renders dynamic API client wrappers based on Jinja2 templates and 
    extracted structural API schemas.
    """
    def __init__(self, template_dir: Optional[str] = None):
        if template_dir is None:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            template_dir = os.path.join(base_dir, "templates")
        self.template_dir = template_dir
        # Ensure template dir exists
        os.makedirs(self.template_dir, exist_ok=True)
        
        # Configure Jinja2 environment
        self.env = Environment(
            loader=FileSystemLoader(self.template_dir),
            trim_blocks=True,
            lstrip_blocks=True
        )

    def validate_schema(self, schema: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate schema data using Pydantic models.
        Returns the validated data as a cleaned dictionary.
        """
        try:
            model_inst = APISchemaModel(**schema)
            if hasattr(model_inst, "model_dump"):
                validated_dict = model_inst.model_dump()
            else:
                validated_dict = model_inst.dict()
        except Exception as e:
            logger.error(f"Schema validation error via Pydantic: {e}")
            raise ValueError(f"Schema validation error: {e}")
            
        # Extra checks:
        if len(validated_dict.get("endpoints") or []) == 0:
            raise ValueError("Schema validation error: 'endpoints' list is missing, invalid, or empty.")
            
        import re
        for ep in validated_dict["endpoints"]:
            name = ep["name"]
            if not re.match(r'^[a-z0-9_]+$', name):
                raise ValueError(f"Schema validation error: Endpoint method name '{name}' must be snake_case.")
                
            param_names = [p["name"] for p in ep["parameters"]]
            if len(param_names) != len(set(param_names)):
                raise ValueError(f"Schema validation error: Endpoint '{name}' has duplicate parameter names: {param_names}")
                
        return validated_dict

    def _format_python_code(self, code: str) -> str:
        """
        Runs autoflake, isort, and black on the generated code using a temp file.
        Falls back to uv run or original code gracefully on failure or if tools are missing.
        """
        import tempfile
        import subprocess
        
        # Write to a temp file
        with tempfile.NamedTemporaryFile(suffix=".py", delete=False, mode="w", encoding="utf-8") as f:
            temp_name = f.name
            f.write(code)
            
        try:
            # 1. Run autoflake to remove unused imports
            try:
                subprocess.run(
                    ["autoflake", "--remove-all-unused-imports", "--in-place", temp_name],
                    capture_output=True, check=False
                )
            except FileNotFoundError:
                subprocess.run(
                    ["uv", "run", "autoflake", "--remove-all-unused-imports", "--in-place", temp_name],
                    capture_output=True, check=False
                )
                
            # 2. Run isort to organize imports
            try:
                subprocess.run(
                    ["isort", temp_name],
                    capture_output=True, check=False
                )
            except FileNotFoundError:
                subprocess.run(
                    ["uv", "run", "isort", temp_name],
                    capture_output=True, check=False
                )
                
            # 3. Run black to format code
            try:
                subprocess.run(
                    ["black", "--line-length", "88", temp_name],
                    capture_output=True, check=False
                )
            except FileNotFoundError:
                subprocess.run(
                    ["uv", "run", "black", "--line-length", "88", temp_name],
                    capture_output=True, check=False
                )
                
            with open(temp_name, "r", encoding="utf-8") as f:
                formatted_code = f.read()
            return formatted_code
        except Exception as e:
            logger.warning(f"Formatting failed, returning unformatted code: {e}")
            return code
        finally:
            if os.path.exists(temp_name):
                try:
                    os.remove(temp_name)
                except Exception:
                    pass

    def render(self, schema_data: Dict[str, Any], target_language: str) -> str:
        """
        Loads the template corresponding to the target language and renders it 
        with the provided schema dictionary.
        """
        schema_clean = self.validate_schema(schema_data)
        
        lang = target_language.lower().strip()
        
        # Map languages to template file names
        template_map = {
            "python": "python.j2",
            "py": "python.j2",
            "javascript": "javascript.j2",
            "js": "javascript.j2",
            "node": "javascript.j2",
            "nodejs": "javascript.j2"
        }
        
        template_file = template_map.get(lang)
        if not template_file:
            raise ValueError(f"Unsupported target language: {target_language}. Supported: python, javascript.")

        logger.info(f"Rendering template '{template_file}' for language '{lang}'...")
        
        import re
        raw_name = schema_clean.get("api_name", "Client")
        clean_name = "".join(part.capitalize() for part in re.split(r'[^a-zA-Z0-9]', raw_name) if part)
        if not clean_name:
            clean_name = "Client"
        schema_clean["api_name"] = clean_name

        print("\n[GENERATOR]\nStarting...\n")
        import time
        start_time = time.time()

        try:
            template = self.env.get_template(template_file)
            rendered_code = template.render(**schema_clean)
            
            if lang in ("python", "py"):
                rendered_code = self._format_python_code(rendered_code)
                
            elapsed = time.time() - start_time
            print(f"Completed\n\nTime: {elapsed:.1f}s\n")
            return rendered_code
        except Exception as e:
            logger.error(f"Failed to render template '{template_file}': {str(e)}")
            raise RuntimeError(f"Code generation template error: {str(e)}")
