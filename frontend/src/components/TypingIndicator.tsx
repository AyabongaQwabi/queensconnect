export function TypingIndicator() {
  return (
    <div className="w-full">
      <div className="flex items-center gap-1.5 mb-1">
        <span className="text-[10px] font-medium text-gray-400 uppercase tracking-wide">
          Queens Connect
        </span>
        <span className="text-[10px] text-gray-400">is typing</span>
      </div>
      <div className="flex gap-0.5">
        <span
          className="w-1.5 h-1.5 rounded-full bg-gray-400/70 animate-bounce"
          style={{ animationDelay: "0ms" }}
        />
        <span
          className="w-1.5 h-1.5 rounded-full bg-gray-400/70 animate-bounce"
          style={{ animationDelay: "120ms" }}
        />
        <span
          className="w-1.5 h-1.5 rounded-full bg-gray-400/70 animate-bounce"
          style={{ animationDelay: "240ms" }}
        />
      </div>
    </div>
  )
}
