# PreMock AI — Frontend

Next.js 16 application with Supabase authentication, real-time interview UI, and AI-powered reporting.

## Setup

```bash
# Install dependencies
npm install
```

## Environment Variables

Copy the example and fill in your keys:

```bash
cp .env.example .env.local
```

## Run

```bash
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) in your browser.

## Project Structure

```
frontend/
├── public/                 # Static assets
├── src/
│   ├── app/                # Next.js App Router pages
│   │   ├── auth/           # Authentication (login, signup, callback)
│   │   ├── dashboard/      # User dashboard
│   │   ├── interview/      # Interview session pages
│   │   ├── pricing/        # Pricing page
│   │   ├── profile/        # User profile
│   │   ├── report/         # Interview report viewer
│   │   ├── layout.tsx      # Root layout
│   │   ├── page.tsx        # Landing page
│   │   └── globals.css     # Global styles
│   ├── components/
│   │   ├── ui/             # Reusable UI primitives
│   │   ├── layout/         # Layout components (nav, footer)
│   │   └── Sidebar.tsx     # Sidebar navigation
│   ├── hooks/              # Custom React hooks
│   ├── lib/
│   │   ├── supabase/       # Supabase client setup
│   │   └── storage.ts      # Storage utilities
│   ├── types/
│   │   └── index.ts        # Shared TypeScript definitions
│   └── middleware.ts       # Auth middleware
├── .env.example
├── next.config.ts
├── vercel.json
└── package.json
```
