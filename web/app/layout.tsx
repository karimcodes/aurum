import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { Providers } from "./providers";
import { Navigation } from "@/components/ui/Navigation";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "Nexus Alpha",
  description: "Quantitative Signal Aggregation & Market Intelligence Platform",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className={inter.className}>
        <Providers>
          <div className="min-h-screen bg-gray-50">
            <Navigation />
            <main className="container mx-auto px-4 py-6">{children}</main>
          </div>
        </Providers>
      </body>
    </html>
  );
}
