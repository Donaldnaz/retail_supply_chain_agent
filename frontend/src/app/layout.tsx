import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Retail Supply Chain Agent",
  description: "Retail supply chain operations and reorder approval assistant",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
