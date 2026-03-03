import { useState, FormEvent, useRef, useEffect } from "react"

const MIN_ROWS = 1
const MAX_ROWS = 8

function isTouchDevice(): boolean {
  if (typeof window === "undefined") return false
  return "ontouchstart" in window || navigator.maxTouchPoints > 0
}

type ChatInputProps = {
  onSend: (message: string) => void
  disabled?: boolean
  placeholder?: string
}

export function ChatInput({
  onSend,
  disabled,
  placeholder = "What's on your mind?",
}: ChatInputProps) {
  const [value, setValue] = useState("")
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  const adjustHeight = () => {
    const el = textareaRef.current
    if (!el) return
    el.style.height = "auto"
    const lineHeight = 22
    const minHeight = 40
    const maxHeight = lineHeight * MAX_ROWS
    const newHeight = Math.min(Math.max(el.scrollHeight, minHeight), maxHeight)
    el.style.height = `${newHeight}px`
  }

  useEffect(() => {
    adjustHeight()
  }, [value])

  const handleSubmit = (e?: FormEvent) => {
    e?.preventDefault()
    const trimmed = value.trim()
    if (!trimmed || disabled) return
    onSend(trimmed)
    setValue("")
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto"
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key !== "Enter") return
    const isTouch = isTouchDevice()
    if (e.shiftKey) {
      // Shift+Enter: always new line
      return
    }
    // Enter without Shift
    if (isTouch) {
      // On mobile: Enter adds new line; user sends via button
      return
    }
    // Desktop: Enter sends
    e.preventDefault()
    handleSubmit()
  }

  return (
    <form
      onSubmit={(e) => {
        e.preventDefault()
        handleSubmit(e)
      }}
      className="flex gap-2 sm:gap-3 items-end rounded-xl border border-gray-200 bg-gray-50 focus-within:border-violet-300 focus-within:ring-2 focus-within:ring-violet-100 transition-all"
    >
      <textarea
        ref={textareaRef}
        value={value}
        onChange={(e) => setValue(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder={placeholder}
        disabled={disabled}
        rows={MIN_ROWS}
        className="flex-1 min-h-[2.5rem] max-h-40 resize-none bg-transparent px-3 py-2.5 text-sm sm:text-base text-gray-900 placeholder-gray-400 focus:outline-none disabled:opacity-50 overflow-y-auto"
        style={{ minHeight: "2.5rem" }}
        aria-label="Message"
      />
      <button
        type="submit"
        disabled={disabled || !value.trim()}
        className="shrink-0 w-9 h-9 sm:w-10 sm:h-10 rounded-full bg-violet-600 hover:bg-violet-700 text-white flex items-center justify-center disabled:opacity-50 disabled:cursor-not-allowed transition-colors mb-1 mr-1"
        aria-label="Send"
      >
        <svg
          className="w-4 h-4 sm:w-5 sm:h-5"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
          aria-hidden
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8"
          />
        </svg>
      </button>
    </form>
  )
}
