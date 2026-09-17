"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { supabase } from "@/lib/supabase/client";

export default function AuthCallbackPage() {
    const router = useRouter();

    useEffect(() => {
        // Supabase automatically handles the token from the URL hash
        // Just redirect to dashboard after auth is confirmed
        supabase.auth.getSession().then(({ data: { session } }) => {
            if (session) {
                router.push("/dashboard");
            } else {
                // Wait a moment for Supabase to process the OAuth code
                setTimeout(() => {
                    router.push("/dashboard");
                }, 2000);
            }
        });
    }, [router]);

    return (
        <div className="min-h-screen bg-background flex items-center justify-center">
            <div className="text-center">
                <div className="w-12 h-12 border-4 border-primary border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
                <p className="text-white font-semibold text-lg">Signing you in...</p>
                <p className="text-zinc-400 text-sm mt-1">Please wait while we set up your account.</p>
            </div>
        </div>
    );
}
