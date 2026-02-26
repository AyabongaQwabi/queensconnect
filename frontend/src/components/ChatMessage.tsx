import type { Components } from "react-markdown"
import ReactMarkdown from "react-markdown"
import remarkGfm from "remark-gfm"

type ChatMessageProps = {
  role: "user" | "assistant"
  content: string
  responseTimeMs?: number
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

export function ChatMessage({ role, content, responseTimeMs }: ChatMessageProps) {
  const isUser = role === "user"

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

  // Assistant: render as markdown (bold, lists, links, etc.)
  return (
    <div className="w-full">
      <div className="flex items-center gap-2 mb-1.5">
        <span className="text-sm font-semibold text-gray-900">Queens Connect</span>
        {responseTimeMs != null && (
          <span className="text-xs text-gray-400" title="Response time">
            {formatResponseTime(responseTimeMs)}
          </span>
        )}
      </div>
      <div className="text-gray-800 break-words max-w-none [&_a]:text-blue-600 [&_a]:underline [&_a]:hover:text-blue-800 [&_a]:cursor-pointer [&_a]:break-all">
        <ReactMarkdown remarkPlugins={[remarkGfm]} components={markdownComponents}>{content}</ReactMarkdown>
      </div>
    </div>
  )
}
