'use client'

import Link from 'next/link'
import { BookOpen, Database, FlaskConical, Search, Upload } from 'lucide-react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'

const cards = [
  {
    icon: BookOpen,
    title: 'Knowledge Library',
    description: 'Manage knowledge bases and view ingested documents.',
    href: '/admin/library',
    cta: 'Open library',
  },
  {
    icon: Upload,
    title: 'Upload Documents',
    description: 'Upload PDFs, DOCX, PPTX, Markdown and more.',
    href: '/admin/upload',
    cta: 'Upload now',
  },
  {
    icon: Search,
    title: 'Search Playground',
    description: 'Test semantic search against the knowledge base.',
    href: '/admin/search',
    cta: 'Open playground',
  },
  {
    icon: Database,
    title: 'Vector Statistics',
    description: 'Inspect the Qdrant collection and indexed vectors.',
    href: '/admin/vector',
    cta: 'View stats',
  },
  {
    icon: FlaskConical,
    title: 'RAG Console',
    description: 'Test curriculum-filtered retrieval with live observability.',
    href: '/admin/rag',
    cta: 'Open console',
  },
]

export function AdminOverview() {
  return (
    <div className="flex flex-col gap-6 p-6">
      <div>
        <h1 className="text-xl font-semibold">Admin Panel</h1>
        <p className="text-sm text-muted-foreground">
          Manage the Roognis AI Context Intelligence Layer.
        </p>
      </div>
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {cards.map(({ icon: Icon, title, description, href, cta }) => (
          <Card key={title} className="group transition-colors hover:border-primary/30">
            <CardHeader className="pb-2">
              <div className="mb-1 inline-flex rounded-lg bg-primary/10 p-2 w-fit">
                <Icon className="h-5 w-5 text-primary" />
              </div>
              <CardTitle className="text-base">{title}</CardTitle>
              <CardDescription className="text-xs">{description}</CardDescription>
            </CardHeader>
            <CardContent>
              <Button size="sm" variant="outline" asChild>
                <Link href={href}>{cta}</Link>
              </Button>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  )
}
