import { useState, FormEvent } from "react"

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

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault()
    const trimmed = value.trim()
    if (!trimmed || disabled) return
    onSend(trimmed)
    setValue("")
  }

  return (
    <form
      onSubmit={handleSubmit}
      className="flex gap-3 items-end rounded-2xl border border-gray-200 bg-gray-50 focus-within:border-[#7c3aed] focus-within:ring-2 focus-within:ring-[#ede9fe] transition-all"
    >
      <input
        type="text"
        value={value}
        onChange={(e) => setValue(e.target.value)}
        placeholder={placeholder}
        disabled={disabled}
        className="flex-1 bg-transparent px-4 py-3 text-sm sm:text-base text-gray-900 placeholder-gray-400 focus:outline-none disabled:opacity-50"
        aria-label="Message"
      />
      <button
        type="submit"
        disabled={disabled || !value.trim()}
        className="shrink-0 w-10 h-10 rounded-full bg-[#7c3aed] hover:bg-[#6d28d9] text-white flex items-center justify-center disabled:opacity-50 disabled:cursor-not-allowed transition-colors mb-1 mr-1"
        aria-label="Send"
      >
        <svg
          className="w-5 h-5"
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
