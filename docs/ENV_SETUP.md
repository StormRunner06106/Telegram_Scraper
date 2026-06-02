# Environment Variables Setup

## Quick Setup

### 1. Check Current Configuration

```bash
python check_env.py
```

This will show you which environment variables are set and which need configuration.

### 2. Edit .env File

The `.env` file is already created with your GitHub token. You just need to add your Supabase credentials:

```bash
# Open .env in your editor
notepad .env        # Windows
nano .env           # Linux/Mac
```

### 3. Get Supabase Credentials

1. Go to your Supabase Dashboard: https://supabase.com/dashboard
2. Select your project
3. Go to **Project Settings** â†’ **API**
4. Copy:
   - **Project URL** (e.g., `https://xxxxx.supabase.co`)
   - **anon/public key** (long string starting with `eyJ...`)

### 4. Update .env File

Replace the placeholder values:

```env
# GitHub Configuration
GITHUB_TOKEN=your_github_token_here

# Supabase Configuration
SUPABASE_URL=https://your-actual-project-id.supabase.co
SUPABASE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...your-actual-key
```

### 5. Verify Configuration

```bash
python check_env.py
```

You should see:

```
âœ… GITHUB_TOKEN: your_github_token_here
âœ… SUPABASE_URL: https://xxxxx.supabase.co
âœ… SUPABASE_KEY: eyJhbGciOiJIUzI...
```

## .env File Format

```env
# GitHub Configuration
GITHUB_TOKEN=your_github_token_here

# Supabase Configuration
SUPABASE_URL=https://your-project-id.supabase.co
SUPABASE_KEY=your_supabase_anon_key_here
```

## Important Notes

### Security

- âœ… `.env` is in `.gitignore` (won't be committed to git)
- âœ… Never share your `.env` file
- âœ… Never commit tokens to git
- âœ… Use `.env.example` as a template for others

### GitHub Token

**Already configured!** Your GitHub token is already in the `.env` file:

```
GITHUB_TOKEN=your_github_token_here
```

If you need a new token:

1. Go to https://github.com/settings/tokens
2. Click "Generate new token (classic)"
3. Select scopes: `public_repo`, `read:user`
4. Copy the token and update `.env`

### Supabase Credentials

**Need to be configured!** Follow these steps:

1. **Get Project URL**:
   - Supabase Dashboard â†’ Project Settings â†’ API
   - Copy "Project URL"
   - Example: `https://abcdefghijk.supabase.co`

2. **Get Anon Key**:
   - Same page (Project Settings â†’ API)
   - Copy "anon/public" key
   - It's a long string starting with `eyJ...`

3. **Update .env**:
   ```env
   SUPABASE_URL=https://abcdefghijk.supabase.co
   SUPABASE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImFiY2RlZmdoaWprIiwicm9sZSI6ImFub24iLCJpYXQiOjE2ODAwMDAwMDAsImV4cCI6MTk5NTU3NjAwMH0.xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   ```

## Troubleshooting

### "SUPABASE_URL: (not set)"

Edit `.env` and add:

```env
SUPABASE_URL=https://your-project-id.supabase.co
```

### "SUPABASE_KEY: (not set)"

Edit `.env` and add:

```env
SUPABASE_KEY=your_supabase_anon_key_here
```

### "Replace with your actual Supabase project URL"

You're still using the placeholder value. Replace it with your real Supabase URL.

### Can't find Supabase credentials

1. Go to https://supabase.com/dashboard
2. Click on your project
3. Click "Project Settings" (gear icon)
4. Click "API" in the left sidebar
5. Copy "Project URL" and "anon public" key

## Verification Checklist

Run `python check_env.py` and verify:

- [ ] âœ… GITHUB_TOKEN is set (already configured)
- [ ] âœ… SUPABASE_URL is set (needs your URL)
- [ ] âœ… SUPABASE_KEY is set (needs your key)
- [ ] No âš ï¸ warnings about placeholder values

## Next Steps

Once all environment variables are configured:

```bash
# 1. Verify configuration
python check_env.py

# 2. Setup Supabase tables
python setup_supabase.py
# Select option 1: Insert/Update regions

# 3. Test setup
python test_setup.py

# 4. Run scraper
python gscraper.py
```

## Quick Commands

```bash
# Check environment
python check_env.py

# Edit .env file
notepad .env        # Windows
nano .env           # Linux/Mac
vim .env            # Linux/Mac (advanced)

# Verify after editing
python check_env.py
```

## Example .env File

Here's what a properly configured `.env` file looks like:

```env
# GitHub Configuration
GITHUB_TOKEN=your_github_token_here

# Supabase Configuration
SUPABASE_URL=https://abcdefghijk.supabase.co
SUPABASE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImFiY2RlZmdoaWprIiwicm9sZSI6ImFub24iLCJpYXQiOjE2ODAwMDAwMDAsImV4cCI6MTk5NTU3NjAwMH0.xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

## Support

If you're still having issues:

1. Run `python check_env.py` and share the output
2. Check `SETUP_GUIDE.md` for detailed setup instructions
3. Verify your Supabase project is active
4. Make sure you copied the correct credentials

---

**Ready?** Run `python check_env.py` to verify your setup! âœ…
