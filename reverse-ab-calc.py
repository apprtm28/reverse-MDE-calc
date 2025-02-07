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
        # Calculate the alternative conversion rate
        alternative_rate = baseline_rate * (1 + effect_size)
        
        # Calculate pooled standard error
        p1, p2 = baseline_rate, alternative_rate
        se = np.sqrt((p1 * (1-p1) + p2 * (1-p2)) / sample_size)
        
        # Calculate z-score for the difference
        z_score = (p2 - p1) / se
        
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

def main():
    st.set_page_config(page_title="Reverse A/B Test Calculator", layout="wide")
    
    st.title("Reverse A/B Test Calculator")
    st.markdown("""
    This calculator helps you find the **Minimum Detectable Effect (MDE)** given your sample size.
    It's based on Evan Miller's sample size calculator methodology, but works in reverse.
    """)
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("Calculator")
        sample_size = st.number_input(
            "Sample Size (per variation):",
            min_value=100,
            value=10000,
            step=100,
            help="Number of subjects in each variation (A and B groups)"
        )
        
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
        
        mde = calculate_mde(sample_size, baseline_rate, power, significance)
        
        st.markdown("---")
        st.subheader("Results")
        
        col_res1, col_res2 = st.columns(2)
        with col_res1:
            st.metric(
                "Minimum Detectable Effect (Relative)",
                f"{mde*100:.2f}%"
            )
        with col_res2:
            st.metric(
                "Absolute Change Detectable",
                f"{baseline_rate * mde * 100:.2f}%"
            )
            
        st.markdown(f"""
        With {sample_size:,} samples per variation, you can detect a relative change of at least **{mde*100:.2f}%**
        from your baseline rate of {baseline_rate*100:.1f}%.
        
        This means:
        - Baseline rate: {baseline_rate*100:.1f}%
        - Minimum detectable rate: {(baseline_rate * (1 + mde))*100:.1f}%
        - Total sample size needed: {sample_size*2:,} (across both variations)
        """)
    
    with col2:
        st.subheader("Power Analysis")
        
        # Create power curve
        effect_sizes = np.linspace(mde*0.5, mde*1.5, 100)
        powers = []
        for effect in effect_sizes:
            p1 = baseline_rate
            p2 = baseline_rate * (1 + effect)
            se = np.sqrt((p1 * (1-p1) + p2 * (1-p2)) / sample_size)
            z_score = (p2 - p1) / se
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
                     annotation_text=f"MDE ({mde*100:.1f}%)")
        
        fig.update_layout(
            title="Statistical Power vs Effect Size",
            xaxis_title="Effect Size (%)",
            yaxis_title="Statistical Power",
            height=400
        )
        
        st.plotly_chart(fig, use_container_width=True)

if __name__ == "__main__":
    main() 