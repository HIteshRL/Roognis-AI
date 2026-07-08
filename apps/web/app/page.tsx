import Link from 'next/link'
import { BrainCircuit, Sparkles, Target, Zap } from 'lucide-react'
import { Button } from '@/components/ui/button'

const features = [
  {
    icon: BrainCircuit,
    title: 'AI-Native Learning',
    description: 'An intelligent system that adapts to how you learn, not how a textbook does.',
  },
  {
    icon: Target,
    title: 'Measurable Progress',
    description: 'Every session tracked. Every concept mapped. Your growth is always visible.',
  },
  {
    icon: Zap,
    title: 'Instant Answers',
    description: 'Ask anything. Get clear, accurate answers powered by frontier LLMs.',
  },
  {
    icon: Sparkles,
    title: 'Personalized Path',
    description: 'Your learning journey is unique. Roognis builds it with you, not for you.',
  },
]

export default function LandingPage() {
  return (
    <div className="flex min-h-screen flex-col bg-background">
      {/* Header */}
      <header className="sticky top-0 z-50 flex h-14 items-center justify-between border-b border-border/50 bg-background/80 px-6 backdrop-blur">
        <div className="flex items-center gap-2">
          <BrainCircuit className="h-6 w-6 text-primary" />
          <span className="text-lg font-semibold">Roognis AI</span>
        </div>
        <div className="flex items-center gap-3">
          <Button variant="ghost" size="sm" asChild>
            <Link href="/student">Dashboard</Link>
          </Button>
          <Button size="sm" asChild>
            <Link href="/chat">Open the tutor</Link>
          </Button>
        </div>
      </header>

      {/* Hero */}
      <section className="flex flex-1 flex-col items-center justify-center px-6 py-32 text-center">
        <div className="mb-4 inline-flex items-center gap-2 rounded-full border border-primary/30 bg-primary/10 px-3 py-1 text-xs font-medium text-primary">
          <Sparkles className="h-3 w-3" />
          AI-Native Learning OS
        </div>
        <h1 className="mx-auto max-w-3xl text-5xl font-bold tracking-tight md:text-6xl">
          Learn anything.
          <br />
          <span className="text-primary">Know where you stand.</span>
        </h1>
        <p className="mx-auto mt-6 max-w-xl text-lg text-muted-foreground">
          Roognis is a personalized, AI-driven learning operating system. It does not teach you
          — it learns how you learn.
        </p>
        <div className="mt-10 flex flex-col gap-3 sm:flex-row">
          <Button size="lg" asChild>
            <Link href="/chat">Start learning</Link>
          </Button>
          <Button size="lg" variant="outline" asChild>
            <Link href="/student">View my dashboard</Link>
          </Button>
        </div>
      </section>

      {/* Features */}
      <section className="border-t border-border/50 px-6 py-20">
        <div className="mx-auto max-w-5xl">
          <h2 className="mb-12 text-center text-3xl font-bold">Built differently.</h2>
          <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
            {features.map(({ icon: Icon, title, description }) => (
              <div
                key={title}
                className="group rounded-xl border border-border bg-card p-5 transition-colors hover:border-primary/30"
              >
                <div className="mb-3 inline-flex rounded-lg bg-primary/10 p-2">
                  <Icon className="h-5 w-5 text-primary" />
                </div>
                <h3 className="mb-2 font-semibold">{title}</h3>
                <p className="text-sm text-muted-foreground">{description}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-border/50 px-6 py-6 text-center text-xs text-muted-foreground">
        © {new Date().getFullYear()} Roognis AI · Phase 0.1
      </footer>
    </div>
  )
}
