import React, { useEffect } from 'react';
import { CheckCircle2, XCircle, AlertCircle, X } from 'lucide-react';

export interface ToastMessage {
  id: string;
  message: string;
  type: 'success' | 'error' | 'info';
}

interface ToastProps {
  toasts: ToastMessage[];
  onClose: (id: string) => void;
}

export const Toast: React.FC<ToastProps> = ({ toasts, onClose }) => {
  return (
    <div className="fixed top-4 right-4 z-50 flex flex-col gap-2 max-w-sm w-full pointer-events-none">
      {toasts.map((toast) => (
        <ToastItem key={toast.id} toast={toast} onClose={onClose} />
      ))}
    </div>
  );
};

interface ToastItemProps {
  toast: ToastMessage;
  onClose: (id: string) => void;
}

const ToastItem: React.FC<ToastItemProps> = ({ toast, onClose }) => {
  useEffect(() => {
    const timer = setTimeout(() => {
      onClose(toast.id);
    }, 4000);
    return () => clearTimeout(timer);
  }, [toast, onClose]);

  const getToastStyle = () => {
    switch (toast.type) {
      case 'success':
        return {
          bg: 'bg-zinc-900 border-successGreen/20',
          icon: <CheckCircle2 className="h-4 w-4 text-successGreen" />,
        };
      case 'error':
        return {
          bg: 'bg-zinc-900 border-errorRed/20',
          icon: <XCircle className="h-4 w-4 text-errorRed" />,
        };
      case 'info':
      default:
        return {
          bg: 'bg-zinc-900 border-accentCyan/20',
          icon: <AlertCircle className="h-4 w-4 text-accentCyan" />,
        };
    }
  };

  const style = getToastStyle();

  return (
    <div
      className={`pointer-events-auto flex items-center justify-between gap-3 p-3.5 rounded-xl border shadow-lg backdrop-blur-md animate-slide-in ${style.bg}`}
    >
      <div className="flex items-center gap-2.5">
        {style.icon}
        <span className="text-xs font-semibold text-gray-200">{toast.message}</span>
      </div>
      <button
        onClick={() => onClose(toast.id)}
        className="p-0.5 text-zinc-500 hover:text-white rounded transition-colors"
      >
        <X className="h-3.5 w-3.5" />
      </button>

      <style>{`
        @keyframes slideIn {
          from {
            transform: translateY(-10px);
            opacity: 0;
          }
          to {
            transform: translateY(0);
            opacity: 1;
          }
        }
        .animate-slide-in {
          animation: slideIn 0.25s cubic-bezier(0.16, 1, 0.3, 1) forwards;
        }
      `}</style>
    </div>
  );
};
