import streamlit as st
import numpy as np
from scipy import stats
import plotly.graph_objects as go

def calculate_mde(sample_size, baseline_rate, power=0.8, significance_level=0.05):
    """
    Calculate the Minimum Detectable Effect given sample size and other parameters.
    Uses binary search to find the smallest effect size that achieves the desired power.
    """
    def power_analysis(effect_size):
        # Calculate the alternative conversion rate (handles both positive and negative effects)
        alternative_rate = baseline_rate * (1 + effect_size)
        
        # Calculate pooled standard error
        p1, p2 = baseline_rate, alternative_rate
        se = np.sqrt((p1 * (1-p1) + p2 * (1-p2)) / sample_size)
        
        # Calculate z-score for the difference
        z_score = abs(p2 - p1) / se  # Use absolute value for two-sided test
        
        # Calculate power
        critical_value = stats.norm.ppf(1 - significance_level/2)
        actual_power = 1 - stats.norm.cdf(critical_value - z_score)
        
        return actual_power - power

    # Binary search for MDE
    left, right = 0.0001, 1.0
    while right - left > 0.0001:
        mid = (left + right) / 2
        if power_analysis(mid) < 0:
            left = mid
        else:
            right = mid
    
    return (left + right) / 2

def calculate_required_sample_size(mde, baseline_rate, power=0.8, significance_level=0.05):
    """
    Calculate required sample size per variation given MDE and other parameters.
    Uses binary search to find the smallest sample size that achieves the desired power.
    """
    def power_analysis(n):
        # Calculate the alternative conversion rate
        alternative_rate = baseline_rate * (1 + mde)
        
        # Calculate pooled standard error
        p1, p2 = baseline_rate, alternative_rate
        se = np.sqrt((p1 * (1-p1) + p2 * (1-p2)) / n)
        
        # Calculate z-score for the difference
        z_score = (p2 - p1) / se
        
        # Calculate power
        critical_value = stats.norm.ppf(1 - significance_level/2)
        actual_power = 1 - stats.norm.cdf(critical_value - z_score)
        
        return actual_power - power

    # Binary search for sample size
    left, right = 100, 10000000  # Reasonable bounds for sample size
    while right - left > 100:  # Precision of 100 samples
        mid = (left + right) // 2
        if power_analysis(mid) < 0:
            left = mid
        else:
            right = mid
    
    return right  # Return the conservative estimate

def main():
    st.set_page_config(page_title="Multi-Mode A/B Test Calculator", layout="wide")
    
    st.title("Multi-Mode A/B Test Calculator")
    st.markdown("""
    This calculator helps you find the **Minimum Detectable Effect (MDE)** given your sample size, or vice versa.
    It's based on Evan Miller's sample size calculator methodology, with additional flexibility.
    """)
    
    # Mode selection
    mode = st.radio(
        "Select Calculator Mode:",
        ["Calculate from sample size", "Calculate from total population"],
        horizontal=True,
        help="Choose whether to start with sample size per variation or total population"
    )
    
    # Calculator section
    st.subheader("Calculator")
    
    # Common parameters
    baseline_rate = st.number_input(
        "Baseline Conversion Rate (%):",
        min_value=0.01,
        max_value=99.99,
        value=30.0,
        step=0.01,
        format="%.2f",
        help="Your current (baseline) conversion rate in percentage"
    ) / 100  # Convert percentage to decimal
    
    power = st.slider(
        "Statistical Power (1-β):",
        min_value=0.5,
        max_value=0.99,
        value=0.8,
        format="%0.2f",
        help="Probability of detecting a true effect (typically 0.8 or 80%)"
    )
    
    significance = st.slider(
        "Significance Level (α):",
        min_value=0.01,
        max_value=0.10,
        value=0.05,
        format="%0.2f",
        help="Probability of false positive (typically 0.05 or 5%)"
    )
    
    # Mode-specific inputs
    if mode == "Calculate from sample size":
        col_sample, col_mde = st.columns(2)
        
        with col_sample:
            sample_size = st.number_input(
                "Sample Size (per variation):",
                min_value=100,
                value=10000,
                step=100,
                help="Number of subjects in each variation"
            )
            
            # Calculate MDE based on sample size
            mde = calculate_mde(sample_size, baseline_rate, power, significance)
            
        with col_mde:
            user_mde = st.number_input(
                "Or set desired MDE (%):",
                min_value=0.1,
                max_value=100.0,
                value=float(mde*100),
                step=0.1,
                format="%.1f",
                help="Set your desired Minimum Detectable Effect"
            ) / 100
            
            # Calculate required sample size based on user's MDE
            required_sample_size = calculate_required_sample_size(
                user_mde, baseline_rate, power, significance
            )
        
    else:  # Calculate from total population
        col_pop, col_var = st.columns(2)
        
        with col_pop:
            total_population = st.number_input(
                "Total Population Size:",
                min_value=200,
                value=20000,
                step=100,
                help="Total number of subjects available"
            )
        
        with col_var:
            num_variants = st.number_input(
                "Number of Variants:",
                min_value=2,
                max_value=10,
                value=2,
                step=1,
                help="Number of variations to test (e.g., 2 for A/B, 3 for A/B/C)"
            )
        
        # Calculate sample size per variation
        sample_size = total_population // num_variants
        
        # Calculate MDE based on sample size
        mde = calculate_mde(sample_size, baseline_rate, power, significance)
        
        # Allow user to set desired MDE
        user_mde = st.number_input(
            "Or set desired MDE (%):",
            min_value=0.1,
            max_value=100.0,
            value=float(mde*100),
            step=0.1,
            format="%.1f",
            help="Set your desired Minimum Detectable Effect"
        ) / 100
        
        # Calculate required total population based on user's MDE
        required_sample_size = calculate_required_sample_size(
            user_mde, baseline_rate, power, significance
        )
        required_population = required_sample_size * num_variants
    
    st.markdown("---")
    st.subheader("Results")
    
    if mode == "Calculate from sample size":
        col_res1, col_res2, col_res3 = st.columns(3)
        with col_res1:
            st.metric(
                "Current MDE (Relative)",
                f"±{mde*100:.2f}%"
            )
        with col_res2:
            st.metric(
                "Absolute Change Detectable",
                f"±{baseline_rate * mde * 100:.2f}%"
            )
        with col_res3:
            st.metric(
                "Required Sample Size for Desired MDE",
                f"{required_sample_size:,}"
            )
            
        st.markdown(f"""
        **With current sample size:**
        - {sample_size:,} samples per variation can detect a relative change of **±{mde*100:.2f}%**
        - Baseline rate: {baseline_rate*100:.1f}%
        - Detectable if rate is:
          • ≤ {(baseline_rate * (1 - mde))*100:.1f}% (decrease of {mde*100:.1f}% or more)
          • ≥ {(baseline_rate * (1 + mde))*100:.1f}% (increase of {mde*100:.1f}% or more)
        - Changes smaller than ±{mde*100:.1f}% are in the undetectable zone
        - Total samples needed: {sample_size*2:,} (across all variations)
        
        **With desired MDE of ±{user_mde*100:.1f}%:**
        - You would need {required_sample_size:,} samples per variation
        - Total samples needed: {required_sample_size*2:,} (across all variations)
        """)
    else:
        col_res1, col_res2, col_res3 = st.columns(3)
        with col_res1:
            st.metric(
                "Sample Size per Variation",
                f"{sample_size:,}"
            )
        with col_res2:
            st.metric(
                "Current MDE (Relative)",
                f"±{mde*100:.2f}%"
            )
        with col_res3:
            st.metric(
                "Required Total Population",
                f"{required_population:,}"
            )
        
        st.markdown(f"""
        **With current population split:**
        - Total population of {total_population:,} split into {num_variants} variants
        - {sample_size:,} samples per variation can detect a relative change of **±{mde*100:.2f}%**
        - Baseline rate: {baseline_rate*100:.1f}%
        - Detectable if rate is:
          • ≤ {(baseline_rate * (1 - mde))*100:.1f}% (decrease of {mde*100:.1f}% or more)
          • ≥ {(baseline_rate * (1 + mde))*100:.1f}% (increase of {mde*100:.1f}% or more)
        - Changes smaller than ±{mde*100:.1f}% are in the undetectable zone
        
        **With desired MDE of ±{user_mde*100:.1f}%:**
        - You would need {required_sample_size:,} samples per variation
        - Total population needed: {required_population:,} (for {num_variants} variants)
        """)

    # Power Analysis section moved to bottom
    st.markdown("---")
    st.subheader("Power Analysis")
    
    # Create power curve with both positive and negative effects
    # Adjust range to ±3x MDE for better readability
    max_effect = max(mde * 3, user_mde * 3) if abs(user_mde - mde) > 0.0001 else mde * 3
    effect_sizes = np.linspace(-max_effect, max_effect, 200)
    powers = []
    for effect in effect_sizes:
        p1 = baseline_rate
        p2 = baseline_rate * (1 + effect)
        se = np.sqrt((p1 * (1-p1) + p2 * (1-p2)) / sample_size)
        z_score = abs(p2 - p1) / se
        critical_value = stats.norm.ppf(1 - significance/2)
        actual_power = 1 - stats.norm.cdf(critical_value - z_score)
        powers.append(actual_power)
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=effect_sizes*100,
        y=powers,
        mode='lines',
        name='Power Curve'
    ))
    fig.add_hline(y=power, line_dash="dash", line_color="red",
                 annotation_text=f"Target Power ({power:.0%})")
    fig.add_vline(x=mde*100, line_dash="dash", line_color="green",
                 annotation_text=f"+MDE ({mde*100:.1f}%)")
    fig.add_vline(x=-mde*100, line_dash="dash", line_color="green",
                 annotation_text=f"-MDE ({mde*100:.1f}%)")
    if abs(user_mde - mde) > 0.0001:  # Only show if different from calculated MDE
        fig.add_vline(x=user_mde*100, line_dash="dash", line_color="blue",
                     annotation_text=f"+Desired ({user_mde*100:.1f}%)")
        fig.add_vline(x=-user_mde*100, line_dash="dash", line_color="blue",
                     annotation_text=f"-Desired ({user_mde*100:.1f}%)")
    
    # Add shaded regions for detectable zones
    fig.add_vrect(
        x0=-max_effect*100, x1=-mde*100,
        fillcolor="rgba(0,255,0,0.1)", layer="below", line_width=0,
        annotation=dict(
            text="Detectable<br>Decrease Zone",
            textangle=0,
            font=dict(size=12),
            x=(-max_effect*100 - mde*100)/2,  # Center between start and MDE
            y=0.95,  # Position near top
            showarrow=False,
            yref='paper',
            xref='x'
        )
    )
    fig.add_vrect(
        x0=mde*100, x1=max_effect*100,
        fillcolor="rgba(0,255,0,0.1)", layer="below", line_width=0,
        annotation=dict(
            text="Detectable<br>Increase Zone",
            textangle=0,
            font=dict(size=12),
            x=(max_effect*100 + mde*100)/2,  # Center between MDE and end
            y=0.85,  # Position slightly lower than decrease zone
            showarrow=False,
            yref='paper',
            xref='x'
        )
    )
    
    fig.update_layout(
        title="Statistical Power vs Effect Size",
        xaxis_title="Effect Size (%)",
        yaxis_title="Statistical Power",
        height=500,  # Increased height for better visibility
        showlegend=True,
        # Set x-axis range to ±3x MDE
        xaxis=dict(
            range=[-max_effect*100, max_effect*100],
            tickformat='.1f'
        ),
        # Ensure y-axis starts at 0
        yaxis=dict(
            range=[0, 1],
            tickformat='.0%'
        ),
        # Add some padding at the top for annotations
        margin=dict(t=50, b=50, l=50, r=50)  # Added padding on all sides
    )
    
    st.plotly_chart(fig, use_container_width=True)

if __name__ == "__main__":
    main() 