import { useState, useEffect, useRef } from "react"
import type { Components } from "react-markdown"
import ReactMarkdown from "react-markdown"
import remarkGfm from "remark-gfm"

type ChatMessageProps = {
  role: "user" | "assistant"
  content: string
  responseTimeMs?: number
  quickActions?: string[]
  onQuickAction?: (action: string) => void
}

function formatResponseTime(ms: number): string {
  if (ms < 1000) return `${ms}ms`
  const sec = ms / 1000
  return sec % 1 === 0 ? `${sec}s` : `${sec.toFixed(1)}s`
}

/** Markdown components so links are blue, clickable, and open in new tab */
const markdownComponents: Components = {
  a: ({ href, children, ...props }) => (
    <a
      href={href}
      target="_blank"
      rel="noopener noreferrer"
      className="text-blue-600 underline hover:text-blue-800 visited:text-blue-700 cursor-pointer break-all"
      {...props}
    >
      {children}
    </a>
  ),
  p: ({ children }) => <p className="whitespace-pre-wrap my-2 first:mt-0 last:mb-0">{children}</p>,
  ul: ({ children }) => <ul className="my-2 list-disc pl-5 space-y-0.5">{children}</ul>,
  ol: ({ children }) => <ol className="my-2 list-decimal pl-5 space-y-0.5">{children}</ol>,
  strong: ({ children }) => <strong className="font-semibold">{children}</strong>,
}

export function ChatMessage({ role, content, responseTimeMs, quickActions = [], onQuickAction }: ChatMessageProps) {
  const isUser = role === "user"
  const [menuOpen, setMenuOpen] = useState(false)
  const menuRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!menuOpen) return
    function handleClickOutside(e: MouseEvent) {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setMenuOpen(false)
      }
    }
    document.addEventListener("mousedown", handleClickOutside)
    return () => document.removeEventListener("mousedown", handleClickOutside)
  }, [menuOpen])

  if (isUser) {
    return (
      <div className="flex w-full justify-end">
        <div className="max-w-[85%] rounded-2xl rounded-br-md bg-gray-100 px-4 py-2.5">
          <p className="text-sm sm:text-base whitespace-pre-wrap break-words text-gray-900">
            {content}
          </p>
        </div>
      </div>
    )
  }

  // Assistant: render as markdown (bold, lists, links, etc.) with elegant border and shadow
  const showMenu = quickActions.length > 0 && onQuickAction
  return (
    <div className="w-full">
      <div className="flex items-center gap-2 mb-1.5 flex-wrap">
        <span className="text-sm font-semibold text-gray-900">Queens Connect</span>
        {showMenu && (
          <div className="relative shrink-0" ref={menuRef}>
            <button
              type="button"
              onClick={() => setMenuOpen((o) => !o)}
              className="flex items-center gap-1 rounded-lg border border-gray-300 bg-white px-2 py-1 text-xs font-medium text-gray-700 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-violet-500 focus:ring-offset-1"
              aria-expanded={menuOpen}
              aria-haspopup="listbox"
            >
              Menu
              <span className="text-gray-400">{menuOpen ? "▲" : "▼"}</span>
            </button>
            {menuOpen && (
              <ul
                role="listbox"
                className="absolute left-0 top-full mt-1 z-20 min-w-[200px] max-h-[70vh] overflow-y-auto rounded-xl border border-gray-200 bg-white py-1 shadow-lg ring-1 ring-black/5"
              >
                {quickActions.map((action) => (
                  <li
                    key={action}
                    role="option"
                    onClick={() => {
                      onQuickAction(action)
                      setMenuOpen(false)
                    }}
                    className="px-3 py-2 text-sm text-gray-800 hover:bg-violet-50 cursor-pointer"
                  >
                    {action}
                  </li>
                ))}
              </ul>
            )}
          </div>
        )}
        {responseTimeMs != null && (
          <span className="text-xs text-gray-400" title="Response time">
            {formatResponseTime(responseTimeMs)}
          </span>
        )}
      </div>
      <div className="rounded-xl border border-violet-200/80 bg-gradient-to-br from-white to-violet-50/30 px-4 py-3 shadow-sm shadow-violet-200/40 ring-1 ring-violet-100/50 text-gray-800 break-words max-w-none [&_a]:text-blue-600 [&_a]:underline [&_a]:hover:text-blue-800 [&_a]:cursor-pointer [&_a]:break-all">
        <ReactMarkdown remarkPlugins={[remarkGfm]} components={markdownComponents}>{content}</ReactMarkdown>
      </div>
    </div>
  )
}
