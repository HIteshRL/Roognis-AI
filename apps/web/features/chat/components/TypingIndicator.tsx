import { Avatar } from './MessageBubble'

export function TypingIndicator() {
  return (
    <div className="msg-in flex gap-3">
      <Avatar isUser={false} />
      <div className="flex flex-col gap-1">
        <span className="px-1 text-[11px] font-medium text-muted-foreground">Roognis</span>
        <div className="flex items-center gap-1.5 rounded-2xl rounded-tl-md bg-card/70 px-4 py-3.5 ring-1 ring-border backdrop-blur">
          <span className="h-2 w-2 animate-bounce rounded-full bg-primary/70 [animation-delay:-0.3s]" />
          <span className="h-2 w-2 animate-bounce rounded-full bg-primary/70 [animation-delay:-0.15s]" />
          <span className="h-2 w-2 animate-bounce rounded-full bg-primary/70" />
        </div>
      </div>
    </div>
  )
}
