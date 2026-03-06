import { useState, useEffect, useRef } from "react"
import { createPortal } from "react-dom"
import type { Components } from "react-markdown"
import ReactMarkdown from "react-markdown"
import remarkGfm from "remark-gfm"

export type ChatMessageProps = {
  role: "user" | "assistant"
  content: string
  responseTimeMs?: number
  quickActions?: string[]
  adminQuickActions?: string[]
  onQuickAction?: (action: string) => void
  onRetry?: (content: string) => void
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

export function ChatMessage({ role, content, responseTimeMs, quickActions = [], adminQuickActions, onQuickAction, onRetry }: ChatMessageProps) {
  const isUser = role === "user"
  const [menuOpen, setMenuOpen] = useState(false)
  const [copied, setCopied] = useState(false)
  const menuRef = useRef<HTMLDivElement>(null)
  const dropdownRef = useRef<HTMLUListElement>(null)
  const [dropdownPosition, setDropdownPosition] = useState({ top: 0, left: 0 })

  useEffect(() => {
    if (!menuOpen) return
    function handleClickOutside(e: MouseEvent) {
      const target = e.target as Node
      const inMenu = menuRef.current?.contains(target)
      const inDropdown = dropdownRef.current?.contains(target)
      if (!inMenu && !inDropdown) setMenuOpen(false)
    }
    document.addEventListener("mousedown", handleClickOutside)
    return () => document.removeEventListener("mousedown", handleClickOutside)
  }, [menuOpen])

  // Position dropdown in viewport when opening (for portal)
  useEffect(() => {
    if (menuOpen && menuRef.current) {
      const rect = menuRef.current.getBoundingClientRect()
      setDropdownPosition({ top: rect.bottom + 4, left: rect.left })
    }
  }, [menuOpen])

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(content)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch {
      // ignore
    }
  }

  if (isUser) {
    return (
      <div className="flex w-full justify-end flex-col items-end gap-1">
        <div className="max-w-[85%] rounded-2xl rounded-br-md bg-gray-100 px-4 py-2.5">
          <p className="text-sm sm:text-base whitespace-pre-wrap break-words text-gray-900">
            {content}
          </p>
        </div>
        {onRetry && (
          <button
            type="button"
            onClick={() => onRetry(content)}
            className="flex items-center gap-1 rounded-md px-2 py-1 text-xs text-gray-500 hover:bg-gray-200 hover:text-gray-700 focus:outline-none focus:ring-1 focus:ring-gray-400"
            title="Resend message"
            aria-label="Resend message"
          >
            <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
            Retry
          </button>
        )}
      </div>
    )
  }

  // Assistant: render as markdown (bold, lists, links, etc.) with elegant border and shadow
  const hasAdminActions = adminQuickActions != null && adminQuickActions.length > 0
  const showMenu = (quickActions.length > 0 || hasAdminActions) && onQuickAction
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
            {menuOpen &&
              createPortal(
                <ul
                  ref={dropdownRef}
                  role="listbox"
                  className="fixed z-[100] min-w-[200px] max-h-[70vh] overflow-y-auto rounded-xl border border-gray-200 bg-white py-1 shadow-lg ring-1 ring-black/5"
                  style={{ top: dropdownPosition.top, left: dropdownPosition.left }}
                >
                  {hasAdminActions && (
                    <>
                      <li className="px-3 py-1.5 text-xs font-semibold text-gray-500 uppercase tracking-wide">
                        Admin
                      </li>
                      {adminQuickActions!.map((action) => (
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
                      <li className="my-1 border-t border-gray-100" aria-hidden />
                    </>
                  )}
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
                </ul>,
                document.body
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
      <button
        type="button"
        onClick={handleCopy}
        className="mt-1 flex items-center gap-1 rounded-md px-2 py-1 text-xs text-gray-500 hover:bg-gray-200 hover:text-gray-700 focus:outline-none focus:ring-1 focus:ring-gray-400"
        title={copied ? "Copied!" : "Copy message"}
        aria-label={copied ? "Copied!" : "Copy message"}
      >
        {copied ? (
          <>
            <svg className="w-3.5 h-3.5 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
            </svg>
            Copied!
          </>
        ) : (
          <>
            <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h2m0 0h2a2 2 0 012 2v2m0 6v2a2 2 0 01-2 2h-2m-4 0H6m0 0h2a2 2 0 002-2v-2m0 0V6a2 2 0 012-2h2m0 0h2a2 2 0 012 2v2" />
            </svg>
            Copy
          </>
        )}
      </button>
    </div>
  )
}
