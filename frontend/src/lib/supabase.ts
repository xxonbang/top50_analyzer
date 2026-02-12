import { createClient } from '@supabase/supabase-js';
import { ExpireStorage } from './expire-storage';

const supabaseUrl = import.meta.env.VITE_SUPABASE_URL || 'https://fyklcplybyfrfryopzvx.supabase.co';
const supabaseAnonKey = import.meta.env.VITE_SUPABASE_ANON_KEY || '';

export const supabase = createClient(supabaseUrl, supabaseAnonKey, {
  auth: {
    storage: ExpireStorage,
    autoRefreshToken: true,
    persistSession: true,
  },
});
