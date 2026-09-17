import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";

const inter = Inter({ subsets: ["latin"], variable: "--font-inter" });

export const metadata: Metadata = {
  title: "PreMock | Real-Time AI Interview Platform",
  description: "Ace your next interview with our proctored AI interviewer, featuring emotional tracking and dynamic follow-ups.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark" suppressHydrationWarning>
      <body className={`${inter.variable} font-sans`} suppressHydrationWarning>
        {/* Abstract background blobs */}
        <div className="fixed inset-0 overflow-hidden pointer-events-none z-[-1]">
          <div className="absolute -top-[20%] -left-[10%] w-[50%] h-[50%] rounded-full bg-purple-900/20 blur-[120px] mix-blend-screen" />
          <div className="absolute top-[40%] -right-[10%] w-[40%] h-[60%] rounded-full bg-blue-900/20 blur-[150px] mix-blend-screen" />
        </div>
        <main className="min-h-screen">
          {children}
        </main>
      </body>
    </html>
  );
}
