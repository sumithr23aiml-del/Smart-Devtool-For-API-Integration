import React from 'react';
import { motion } from 'framer-motion';
import { Sparkles, ArrowRight, Play } from 'lucide-react';

interface HeroProps {
  onCtaClick: () => void;
  onDemoClick: () => void;
}

export const Hero: React.FC<HeroProps> = ({ onCtaClick, onDemoClick }) => {
  return (
    <div className="relative overflow-hidden py-16 md:py-24 border-b border-white/5">
      {/* Decorative Gradient Background Elements */}
      <div className="absolute inset-0 bg-gradient-to-b from-primaryPurple/5 via-transparent to-transparent pointer-events-none" />
      <div className="absolute top-1/4 left-1/4 h-[300px] w-[300px] rounded-full bg-primaryPurple/10 blur-[80px] pointer-events-none" />
      <div className="absolute top-1/3 right-1/4 h-[350px] w-[350px] rounded-full bg-secondaryBlue/10 blur-[100px] pointer-events-none" />

      <div className="relative z-10 max-w-5xl mx-auto px-6 text-center">
        {/* Sparkle Badge */}
        <motion.div
          initial={{ opacity: 0, y: 15 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6 }}
          className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full border border-white/10 bg-white/5 backdrop-blur-md mb-6 shadow-lg shadow-black/20"
        >
          <Sparkles className="h-4 w-4 text-primaryPurple animate-pulse" />
          <span className="text-xs font-semibold text-gray-200">
            Next-Gen RAG Integration Pipeline
          </span>
        </motion.div>

        {/* Large Bold Heading */}
        <motion.h1
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.15 }}
          className="text-4xl sm:text-6xl font-extrabold tracking-tight text-white mb-6 font-sans leading-none"
        >
          Generate API SDKs Using{' '}
          <span className="bg-gradient-to-r from-primaryPurple via-secondaryBlue to-accentCyan bg-clip-text text-transparent">
            Generative AI
          </span>
        </motion.h1>

        {/* Subtitle */}
        <motion.p
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.3 }}
          className="text-lg sm:text-xl text-gray-400 max-w-2xl mx-auto mb-10 leading-relaxed"
        >
          Paste any API documentation URL and generate production-ready wrapper classes in seconds using RAG + LLMs. No more writing manual API client classes.
        </motion.p>

        {/* Buttons */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.45 }}
          className="flex flex-col sm:flex-row items-center justify-center gap-4"
        >
          <button
            onClick={onCtaClick}
            className="group relative flex items-center justify-center gap-2 w-full sm:w-auto px-8 py-4 rounded-xl bg-gradient-to-r from-primaryPurple to-secondaryBlue text-white font-semibold text-sm shadow-xl shadow-primaryPurple/35 hover:shadow-primaryPurple/50 hover:scale-[1.02] active:scale-[0.98] transition-all duration-200 overflow-hidden"
          >
            <div className="absolute inset-0 bg-white/10 opacity-0 group-hover:opacity-100 transition-opacity" />
            Generate Wrapper
            <ArrowRight className="h-4 w-4 group-hover:translate-x-1 transition-transform" />
          </button>
          
          <button
            onClick={onDemoClick}
            className="flex items-center justify-center gap-2 w-full sm:w-auto px-8 py-4 rounded-xl bg-white/5 border border-white/10 text-white hover:text-white hover:bg-white/10 hover:border-white/20 active:scale-[0.98] font-semibold text-sm transition-all duration-200 shadow-md backdrop-blur-sm"
          >
            <Play className="h-4 w-4 text-accentCyan fill-accentCyan/10" />
            View Demo
          </button>
        </motion.div>
      </div>
    </div>
  );
};
