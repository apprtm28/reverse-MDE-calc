# Multi-Mode A/B Test Calculator

This tool calculates the Minimum Detectable Effect (MDE) for an A/B test given a fixed sample size. It's based on the statistical methodology used in Evan Miller's Sample Size Calculator but works in more flexible ways - instead of calculating the required sample size for a given MDE, it calculates the smallest effect size you can reliably detect with your available sample size.

## Why This Calculator?

Most A/B test calculators tell you how many samples you need for a given effect size. However, in the real world, teams often face fixed traffic constraints or time limitations. This calculator also solves the reverse problem, helping teams understand what they can realistically test with their available sample size. Here's why this is valuable:

1. **Practical Reality Check**: Instead of asking "how many users do I need?" (which you might not be able to control), you can ask "what's the smallest change I can reliably detect?" This helps set realistic expectations for your A/B tests.

2. **Resource Planning**: 
   - If the MDE is too high for your business needs, you know you need to:
     - Wait longer to collect more samples
     - Find ways to increase traffic
     - Or consider other testing approaches
   - If the MDE is lower than needed, you might be able to run shorter tests

3. **Risk Assessment**:
   - Helps teams understand if they have enough statistical power to detect meaningful changes
   - Prevents teams from running underpowered tests that might miss important effects
   - Helps avoid wasting time on tests that can't detect business-relevant changes

4. **Complementary to Standard Calculators**:
   - Traditional calculators tell you required sample size
   - This Multi-Mode calculator can answer the opposite question
   - Together, they provide a complete picture for test planning

5. **Educational Tool**:
   - The visual power analysis curve helps teams understand the relationship between sample size, effect size, and statistical power
   - Makes statistical concepts more tangible for non-technical stakeholders

This calculator is particularly valuable for product teams, growth teams, and anyone doing online experimentation with fixed traffic constraints - a very common real-world scenario.

## Features

- Two calculation modes:
  - Calculate MDE from sample size per variation
  - Calculate MDE from total population size
- Interactive sliders for statistical parameters
- Visual power analysis curve with detectable zones
- Both relative and absolute effect size calculations
- Statistical power and significance level customization
- Real-time updates as you adjust parameters
- Detailed results explanation for each calculation

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

- **Mode Selection**: Choose between calculating from sample size or total population
- **Baseline Conversion Rate**: Your current conversion rate
- **Statistical Power**: Probability of detecting a true effect (typically 0.8)
- **Alpha (α)**: One minus the confidence level (typically 0.05 for 95% confidence)

For "Calculate from sample size" mode:
- **Sample Size**: Number of subjects per variation (A/B groups)
- **Desired MDE**: Optional target minimum detectable effect

For "Calculate from total population" mode:
- **Total Population**: Total number of subjects available
- **Number of Variants**: Number of variations to test (e.g., 2 for A/B, 3 for A/B/C)
- **Desired MDE**: Optional target minimum detectable effect

## How It Works

The calculator uses a binary search algorithm to find the smallest effect size that achieves the desired statistical power. It can work in two modes:

1. **Sample Size Mode**: Given a fixed sample size per variation, it calculates:
   - The minimum detectable effect (MDE)
   - The absolute change that can be detected
   - Required sample size for a desired MDE

2. **Total Population Mode**: Given a total population size, it:
   - Splits the population among the specified number of variants
   - Calculates the MDE based on the per-variant sample size
   - Shows required total population for a desired MDE

The power analysis curve visualizes:
- The relationship between effect size and statistical power
- Detectable increase and decrease zones
- Current MDE thresholds
- Optional desired MDE thresholds

## License

MIT License 