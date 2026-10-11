import { createClient } from '@supabase/supabase-js';

const supabaseUrl = 'https://fotdyidbreamqmyhsyfg.supabase.co';
const supabaseKey = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImZvdGR5aWRicmVhbXFteWhzeWZnIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODY2MTAxMjMsImV4cCI6MjEwMjE4NjEyM30.XTxEL1ZJCpamm4VG9rXQKr0aw5TZJp-QHQ7IgwvoUpw';
const supabase = createClient(supabaseUrl, supabaseKey);

async function test() {
    const { error } = await supabase.from('interview_sessions').insert({
        user_id: '11111111-1111-1111-1111-111111111111', 
        eye_contact_violations: 0, 
        face_detection_violations: 0
    });
    console.log(error);
}
test();
