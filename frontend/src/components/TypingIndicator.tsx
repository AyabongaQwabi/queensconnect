export function TypingIndicator() {
  return (
    <div className="w-full">
      <div className="flex items-center gap-2 mb-1.5">
        <span className="text-sm font-semibold text-gray-900">Queens Connect</span>
      </div>
      <div className="flex gap-1">
        <span
          className="w-2 h-2 rounded-full bg-[#7c3aed]/60 animate-bounce"
          style={{ animationDelay: "0ms" }}
        />
        <span
          className="w-2 h-2 rounded-full bg-[#7c3aed]/60 animate-bounce"
          style={{ animationDelay: "150ms" }}
        />
        <span
          className="w-2 h-2 rounded-full bg-[#7c3aed]/60 animate-bounce"
          style={{ animationDelay: "300ms" }}
        />
      </div>
    </div>
  )
}
