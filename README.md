# Reverse A/B Test Calculator

This tool calculates the Minimum Detectable Effect (MDE) for an A/B test given a fixed sample size. It's based on the statistical methodology used in Evan Miller's Sample Size Calculator but works in reverse - instead of calculating the required sample size for a given MDE, it calculates the smallest effect size you can reliably detect with your available sample size.

## Features

- Calculate MDE given sample size and baseline conversion rate
- Interactive sliders for all parameters
- Visual power analysis curve
- Both relative and absolute effect size calculations
- Statistical power and significance level customization

## Installation

1. Clone this repository
2. Install the required packages:
```bash
pip install -r requirements.txt
```

## Local Usage

Run the Streamlit app locally:
```bash
streamlit run reverse-ab-calc.py
```

Then open your browser and navigate to the URL shown in the terminal (typically http://localhost:8501).

## Deployment

### Deploy to Streamlit Cloud (Recommended)

1. Push your code to a GitHub repository
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Sign in with GitHub
4. Click "New app"
5. Select your repository, branch, and main file path (`reverse-ab-calc.py`)
6. Click "Deploy"

Your app will be live at `https://your-app-name.streamlit.app`

### Alternative Deployment Options

#### Deploy to Heroku
1. Create a `Procfile`:
```
web: streamlit run reverse-ab-calc.py
```
2. Add `setup.sh`:
```bash
mkdir -p ~/.streamlit/
echo "[server]
headless = true
port = $PORT
enableCORS = false
" > ~/.streamlit/config.toml
```
3. Deploy using Heroku CLI or GitHub integration

#### Deploy to Railway.app
1. Push to GitHub
2. Connect your repository to Railway
3. Add the build command: `pip install -r requirements.txt`
4. Add the start command: `streamlit run reverse-ab-calc.py`

## Parameters

- **Sample Size**: Number of subjects per variation (A/B groups)
- **Baseline Conversion Rate**: Your current conversion rate
- **Statistical Power**: Probability of detecting a true effect (typically 0.8)
- **Significance Level**: Probability of false positive (typically 0.05)

## How It Works

The calculator uses a binary search algorithm to find the smallest effect size that achieves the desired statistical power, given your sample size and other parameters. It takes into account:

- The baseline conversion rate
- The required statistical power (typically 80%)
- The significance level (typically 5%)
- The sample size per variation

The power analysis curve shows how the statistical power changes with different effect sizes, helping you understand the sensitivity of your test.

## License

MIT License 