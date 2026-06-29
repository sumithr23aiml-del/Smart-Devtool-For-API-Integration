document.addEventListener('DOMContentLoaded', () => {
    // DOM Elements
    const generatorForm = document.getElementById('generator-form');
    const docUrlInput = document.getElementById('doc-url');
    const useCaseInput = document.getElementById('use-case');
    const targetLangSelect = document.getElementById('target-lang');
    const crawlDepthSelect = document.getElementById('crawl-depth');
    const submitBtn = document.getElementById('submit-btn');
    const submitSpinner = submitBtn.querySelector('.spinner');
    const submitText = submitBtn.querySelector('.btn-text');
    
    // Status tracking steps
    const pipelineStatusDiv = document.getElementById('pipeline-status');
    const stepCrawl = document.getElementById('step-crawl');
    const stepClean = document.getElementById('step-clean');
    const stepVector = document.getElementById('step-vector');
    const stepChroma = document.getElementById('step-chroma');
    const stepLlm = document.getElementById('step-llm');
    const stepGenerator = document.getElementById('step-generator');
    
    // Output tabs
    const tabButtons = document.querySelectorAll('.tab-btn');
    const tabPanes = document.querySelectorAll('.tab-pane');
    const schemaTabBtn = document.getElementById('schema-tab-btn');
    
    // Output containers
    const codeFileName = document.getElementById('code-file-name');
    const codeBlock = document.getElementById('code-block');
    const copyCodeBtn = document.getElementById('copy-code-btn');
    const downloadCodeBtn = document.getElementById('download-code-btn');
    const terminalLogs = document.getElementById('terminal-logs');
    
    // Schema details
    const infoApiName = document.getElementById('info-api-name');
    const infoBaseUrl = document.getElementById('info-base-url');
    const infoAuthType = document.getElementById('info-auth-type');
    const endpointsList = document.getElementById('endpoints-list');

    let generatedCodeString = "";
    let currentCrawlId = null;
    let pollInterval = null;

    // 1. Tab Switching Logic
    const leftTabButtons = document.querySelectorAll('.left-panel .tab-btn');
    const leftTabPanes = document.querySelectorAll('.left-panel .tab-pane');
    
    leftTabButtons.forEach(btn => {
        btn.addEventListener('click', () => {
            const targetTab = btn.getAttribute('data-tab');
            leftTabButtons.forEach(b => b.classList.remove('active'));
            leftTabPanes.forEach(p => p.classList.remove('active'));
            btn.classList.add('active');
            document.getElementById(targetTab).classList.add('active');
        });
    });

    const rightTabButtons = document.querySelectorAll('.right-panel .tab-btn');
    const rightTabPanes = document.querySelectorAll('.right-panel .tab-pane');
    
    rightTabButtons.forEach(btn => {
        btn.addEventListener('click', () => {
            const targetTab = btn.getAttribute('data-tab');
            rightTabButtons.forEach(b => b.classList.remove('active'));
            rightTabPanes.forEach(p => p.classList.remove('active'));
            btn.classList.add('active');
            document.getElementById(targetTab).classList.add('active');
        });
    });

    // 2. Terminal Logger Helper
    function logToTerminal(message, type = 'system') {
        const timestamp = new Date().toLocaleTimeString();
        const line = document.createElement('div');
        line.className = `log-line ${type}`;
        line.innerText = `[${timestamp}] [${type.toUpperCase()}] ${message}`;
        terminalLogs.appendChild(line);
        terminalLogs.parentElement.scrollTop = terminalLogs.parentElement.scrollHeight;
    }

    // 3. Reset pipeline display
    function resetPipelineUI() {
        pipelineStatusDiv.classList.remove('hidden');
        [stepCrawl, stepClean, stepVector, stepChroma, stepLlm, stepGenerator].forEach(step => {
            step.className = 'step';
        });
    }

    // 4. Update timeline active state based on backend actions
    function updatePipelineSteps(action, status) {
        if (status === 'failed') {
            [stepCrawl, stepClean, stepVector, stepChroma, stepLlm, stepGenerator].forEach(step => {
                if (step.classList.contains('active')) {
                    step.classList.remove('active');
                    step.style.color = 'var(--red)';
                }
            });
            return;
        }

        const actionLower = action.toLowerCase();
        
        if (actionLower.includes('crawling')) {
            stepCrawl.className = 'step active';
        } else if (actionLower.includes('cleaning') || actionLower.includes('html')) {
            stepCrawl.className = 'step completed';
            stepClean.className = 'step active';
        } else if (actionLower.includes('chunking') || actionLower.includes('split')) {
            stepCrawl.className = 'step completed';
            stepClean.className = 'step completed';
            stepVector.className = 'step active';
        } else if (actionLower.includes('embedding') || actionLower.includes('vectorizing')) {
            stepCrawl.className = 'step completed';
            stepClean.className = 'step completed';
            stepVector.className = 'step active';
        } else if (actionLower.includes('indexing') || actionLower.includes('chromadb')) {
            stepCrawl.className = 'step completed';
            stepClean.className = 'step completed';
            stepVector.className = 'step completed';
            stepChroma.className = 'step active';
        } else if (status === 'completed') {
            stepCrawl.className = 'step completed';
            stepClean.className = 'step completed';
            stepVector.className = 'step completed';
            stepChroma.className = 'step completed';
        }
    }

    // 5. Submit Form & Start Pipeline
    generatorForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        const url = docUrlInput.value.trim();
        const useCase = useCaseInput.value;
        const lang = targetLangSelect.value;
        const depth = parseInt(crawlDepthSelect.value);

        if (!url) return;

        // Toggle UI loading states
        submitBtn.disabled = true;
        submitSpinner.classList.remove('hidden');
        submitText.innerText = "Processing Index...";
        
        copyCodeBtn.disabled = true;
        downloadCodeBtn.disabled = true;
        schemaTabBtn.disabled = true;
        
        resetPipelineUI();
        logToTerminal(`Initiating API crawl request for: ${url}`, 'info');

        try {
            // Trigger crawler
            const crawlResponse = await fetch('/api/v1/crawl', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ url: url, max_depth: depth })
            });

            if (!crawlResponse.ok) {
                const errData = await crawlResponse.json();
                throw new Error(errData.detail || "Crawl request initiation failed.");
            }

            const crawlData = await crawlResponse.json();
            currentCrawlId = crawlData.crawl_id;
            logToTerminal(`Crawl task registered. ID: ${currentCrawlId}`, 'info');

            // Begin polling status
            startCrawlPolling(currentCrawlId, useCase, lang);

        } catch (error) {
            logToTerminal(error.message, 'error');
            resetSubmitBtn();
        }
    });

    // 6. Polling Crawl Status
    function startCrawlPolling(crawlId, useCase, lang) {
        let lastAction = "";
        
        pollInterval = setInterval(async () => {
            try {
                const statusRes = await fetch(`/api/v1/status/${crawlId}`);
                if (!statusRes.ok) {
                    throw new Error("Failed to check crawl job status.");
                }

                const statusData = await statusRes.json();
                
                if (statusData.current_action !== lastAction && statusData.current_action) {
                    lastAction = statusData.current_action;
                    logToTerminal(`${statusData.current_action}... (Pages found: ${statusData.pages_indexed})`, 'system');
                }

                updatePipelineSteps(statusData.current_action, statusData.status);

                if (statusData.status === 'completed') {
                    clearInterval(pollInterval);
                    logToTerminal(`Document indexing complete! Indexed ${statusData.pages_indexed} pages.`, 'success');
                    
                    // Proceed to Generate SDK Wrapper Code
                    generateWrapperCode(crawlId, useCase, lang);
                } else if (statusData.status === 'failed') {
                    clearInterval(pollInterval);
                    logToTerminal(`Crawling failed: ${statusData.error || "Unknown indexing error"}`, 'error');
                    updatePipelineSteps("", "failed");
                    resetSubmitBtn();
                }

            } catch (error) {
                clearInterval(pollInterval);
                logToTerminal(`Polling error: ${error.message}`, 'error');
                resetSubmitBtn();
            }
        }, 1500);
    }

    // 7. Request Code Generation
    async function generateWrapperCode(crawlId, useCase, lang) {
        logToTerminal(`Sending schema extraction queries using use case: "${useCase}"`, 'info');
        submitText.innerText = "Generating Code...";
        stepLlm.className = 'step active';

        try {
            const genResponse = await fetch('/api/v1/generate', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    crawl_id: crawlId,
                    use_case: useCase,
                    target_language: lang
                })
            });

            if (!genResponse.ok) {
                const errData = await genResponse.json();
                throw new Error(errData.detail || "Wrapper code generation failed.");
            }

            const genData = await genResponse.json();
            
            stepLlm.className = 'step completed';
            stepGenerator.className = 'step completed';
            logToTerminal(`Wrapper client compiled successfully!`, 'success');

            // Set code block text
            generatedCodeString = genData.wrapper_code;
            codeBlock.textContent = generatedCodeString;
            
            // Adjust highlighting parameters
            const extension = lang === 'python' ? 'py' : 'js';
            codeFileName.innerText = `${genData.schema_details.api_name.toLowerCase().replace(/[^a-z0-9]/g, '_')}_client.${extension}`;
            codeBlock.className = `language-${lang}`;
            
            // Trigger syntax highlighter refresh
            Prism.highlightElement(codeBlock);

            // Populate Visual Schema Details
            populateSchemaDetails(genData.schema_details);
            
            // Enable Actions
            copyCodeBtn.disabled = false;
            downloadCodeBtn.disabled = false;
            schemaTabBtn.disabled = false;

        } catch (error) {
            logToTerminal(error.message, 'error');
            stepLlm.style.color = 'var(--red)';
            stepGenerator.style.color = 'var(--red)';
        } finally {
            resetSubmitBtn();
        }
    }

    // 8. Visual Schema Rendering
    function populateSchemaDetails(schema) {
        infoApiName.innerText = schema.api_name || "Unknown API";
        infoBaseUrl.innerText = schema.base_url || "Not Specified";
        infoAuthType.innerText = schema.authentication ? schema.authentication.type.toUpperCase() : "NONE";
        
        endpointsList.innerHTML = "";
        
        if (schema.endpoints && schema.endpoints.length > 0) {
            schema.endpoints.forEach(ep => {
                const item = document.createElement('div');
                item.className = 'endpoint-item';
                
                const methodLower = ep.method.toLowerCase();
                
                item.innerHTML = `
                    <div class="endpoint-header">
                        <span class="method-badge ${methodLower}">${ep.method}</span>
                        <span class="endpoint-path">${ep.path}</span>
                    </div>
                    <div class="endpoint-desc">${ep.description || 'No description extracted.'}</div>
                `;
                endpointsList.appendChild(item);
            });
        } else {
            endpointsList.innerHTML = `<p class="placeholder-text">No endpoints could be parsed into structural parameters.</p>`;
        }
    }

    // 9. Reset Submit Button state
    function resetSubmitBtn() {
        submitBtn.disabled = false;
        submitSpinner.classList.add('hidden');
        submitText.innerText = "Generate Wrapper Client";
    }

    // 10. Copy to clipboard
    copyCodeBtn.addEventListener('click', () => {
        if (!generatedCodeString) return;
        navigator.clipboard.writeText(generatedCodeString)
            .then(() => {
                const origText = copyCodeBtn.innerText;
                copyCodeBtn.innerText = "Copied!";
                copyCodeBtn.style.borderColor = 'var(--green)';
                setTimeout(() => {
                    copyCodeBtn.innerText = origText;
                    copyCodeBtn.style.borderColor = '';
                }, 1500);
            })
            .catch(err => {
                logToTerminal(`Clipboard copy failed: ${err}`, 'error');
            });
    });

    // 11. Download file flow
    downloadCodeBtn.addEventListener('click', () => {
        if (!generatedCodeString) return;
        
        const lang = targetLangSelect.value;
        const extension = lang === 'python' ? 'py' : 'js';
        const filename = codeFileName.innerText || `api_client.${extension}`;
        
        const blob = new Blob([generatedCodeString], { type: 'text/plain;charset=utf-8' });
        const url = URL.createObjectURL(blob);
        
        const link = document.createElement('a');
        link.href = url;
        link.download = filename;
        document.body.appendChild(link);
        link.click();
        
        document.body.removeChild(link);
        URL.revokeObjectURL(url);
    });

    // 12. Interactive AI Assistant Chat Logic
    const chatForm = document.getElementById('chat-form');
    const chatInput = document.getElementById('chat-input');
    const chatMessages = document.getElementById('chat-messages');
    const chatSendBtn = document.getElementById('chat-send-btn');
    const chipBtns = document.querySelectorAll('.chip-btn');
    
    let conversationHistory = [];

    // Quick suggestion chips
    chipBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            const promptText = btn.getAttribute('data-prompt');
            if (promptText) {
                chatInput.value = promptText;
                chatForm.dispatchEvent(new Event('submit', { cancelable: true }));
            }
        });
    });

    // Helper to render Markdown formatting inside chat bubbles safely
    function formatChatMessage(text) {
        let formatted = text
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;");
            
        // Code blocks ```language ... ```
        formatted = formatted.replace(/```(\w+)?\n([\s\S]*?)```/g, (match, lang, code) => {
            const languageClass = lang ? `language-${lang}` : 'language-text';
            return `<pre><code class="${languageClass}">${code.trim()}</code></pre>`;
        });

        // Inline code `code`
        formatted = formatted.replace(/`([^`]+)`/g, '<code>$1</code>');
        // Bold **text**
        formatted = formatted.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
        // Italic *text*
        formatted = formatted.replace(/\*([^*]+)\*/g, '<em>$1</em>');
        // Newlines to <br> outside code blocks
        formatted = formatted.split(/(\<pre[\s\S]*?\<\/pre\>)/g).map((part, idx) => {
            if (idx % 2 === 1) return part; // Inside pre tag
            return part.replace(/\n/g, '<br>');
        }).join('');

        return formatted;
    }

    function appendChatBubble(role, initialText = '') {
        const bubble = document.createElement('div');
        bubble.className = `chat-bubble ${role}`;
        
        const avatarSvg = role === 'assistant' ? `
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
            </svg>
        ` : `
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path>
                <circle cx="12" cy="7" r="4"></circle>
            </svg>
        `;
        const title = role === 'assistant' ? 'Smart DevTool Assistant' : 'You';

        bubble.innerHTML = `
            <div class="bubble-avatar">${avatarSvg}</div>
            <div class="bubble-content">
                <p><strong>${title}</strong></p>
                <div class="message-body">${formatChatMessage(initialText)}</div>
            </div>
        `;

        chatMessages.appendChild(bubble);
        chatMessages.scrollTop = chatMessages.scrollHeight;
        return bubble;
    }

    if (chatForm) {
        chatForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const messageText = chatInput.value.trim();
            if (!messageText) return;

            // Clear input
            chatInput.value = '';
            
            // Append user bubble and track in history
            appendChatBubble('user', messageText);
            conversationHistory.push({ role: 'user', content: messageText });

            // Disable input button while streaming
            chatSendBtn.disabled = true;
            const btnText = chatSendBtn.querySelector('.btn-text');
            const btnSpinner = chatSendBtn.querySelector('.spinner');
            if (btnText) btnText.classList.add('hidden');
            if (btnSpinner) btnSpinner.classList.remove('hidden');

            // Create assistant bubble with cursor
            const assistantBubble = appendChatBubble('assistant', '');
            const messageBody = assistantBubble.querySelector('.message-body');
            messageBody.innerHTML = '<span class="streaming-cursor"></span>';

            let accumulatedText = '';

            try {
                const response = await fetch('/api/v1/chat/stream', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ messages: conversationHistory })
                });

                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}: Chat stream connection failed`);
                }

                const reader = response.body.getReader();
                const decoder = new TextDecoder('utf-8');

                while (true) {
                    const { done, value } = await reader.read();
                    if (done) break;

                    const chunk = decoder.decode(value, { stream: true });
                    accumulatedText += chunk;
                    
                    messageBody.innerHTML = formatChatMessage(accumulatedText) + '<span class="streaming-cursor"></span>';
                    chatMessages.scrollTop = chatMessages.scrollHeight;
                }

                // Remove cursor and final render
                messageBody.innerHTML = formatChatMessage(accumulatedText);
                
                // Highlight any Prism code blocks inside assistant message
                if (window.Prism) {
                    messageBody.querySelectorAll('pre code').forEach(block => {
                        Prism.highlightElement(block);
                    });
                }

                // Track assistant response in conversation history
                conversationHistory.push({ role: 'assistant', content: accumulatedText });

            } catch (error) {
                messageBody.innerHTML = `<span style="color: var(--red);">Error streaming response: ${error.message}</span>`;
            } finally {
                chatSendBtn.disabled = false;
                if (btnText) btnText.classList.remove('hidden');
                if (btnSpinner) btnSpinner.classList.add('hidden');
                chatMessages.scrollTop = chatMessages.scrollHeight;
            }
        });
    }
});

