# Upload to GitHub - Commands

## Step 1: Initialize Git (if not already done)
```bash
git init
```

## Step 2: Add all files
```bash
git add .
```

## Step 3: Commit
```bash
git commit -m "Initial commit: Algorithmic Trading Platform with Anomaly Detection"
```

## Step 4: Create repository on GitHub
- Go to https://github.com/new
- Create a new repository (don't initialize with README)
- Copy the repository URL (e.g., `https://github.com/yourusername/algo_trading.git`)

## Step 5: Add remote and push
```bash
git remote add origin https://github.com/yourusername/algo_trading.git
git branch -M main
git push -u origin main
```

## All Commands Together
```bash
cd "/Users/samueldinkayehu/algorithmic trading with anamoly detection/algo_trading"
git init
git add .
git commit -m "Initial commit: Algorithmic Trading Platform with Anomaly Detection"
git remote add origin https://github.com/yourusername/algo_trading.git
git branch -M main
git push -u origin main
```

**Note**: Replace `yourusername/algo_trading` with your actual GitHub username and repository name.

