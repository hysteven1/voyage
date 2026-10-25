import type { Metadata } from "next";
import { AppRouterCacheProvider } from "@mui/material-nextjs/v16-appRouter";
import VoyageProvider from "@/components/VoyageProvider";
import "./globals.css";

export const metadata: Metadata = {
  title: "Voyage: Your kind of trip",
  description:
    "Big adventures, slow mornings, and everything in between. Plan a personal itinerary with a route and budget that work for you.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en">
      <body>
        <AppRouterCacheProvider options={{ enableCssLayer: true }}>
          <VoyageProvider>{children}</VoyageProvider>
        </AppRouterCacheProvider>
      </body>
    </html>
  );
}
