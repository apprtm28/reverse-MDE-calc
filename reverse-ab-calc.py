import streamlit as st
import numpy as np
from scipy import stats
import plotly.graph_objects as go
import os

# Ensure the app uses the correct port from the environment
port = int(os.environ.get("PORT", 8501))
# Optional debugging message that appears at the top of the app
# st.write(f"Running on port: {port}")

def significance_to_z(significance_level, two_sided=True):
    """Return the critical z-value for a significance level."""
    tail = 2 if two_sided else 1
    return stats.norm.ppf(1 - significance_level / tail)


def two_proportion_power(effect_size, sample_size, baseline_rate,
                         significance_level=0.05, two_sided=True):
    """Statistical power of a two-proportion z-test for a relative effect size.

    Both tails are included for a two-sided test, so a null effect yields a
    power equal to the significance level (the Type I error rate).
    """
    if baseline_rate <= 0 or baseline_rate >= 1:
        return 0.0
    alternative_rate = baseline_rate * (1 + effect_size)
    if alternative_rate <= 0:
        return 0.0
    alternative_rate = min(alternative_rate, 1.0)
    p1, p2 = baseline_rate, alternative_rate
    se = np.sqrt((p1 * (1 - p1) + p2 * (1 - p2)) / sample_size)
    if se <= 0:
        return 0.0
    z_effect = abs(p2 - p1) / se
    critical_value = significance_to_z(significance_level, two_sided)
    power = stats.norm.cdf(z_effect - critical_value)
    if two_sided:
        power += stats.norm.cdf(-z_effect - critical_value)
    return power


def calculate_mde(sample_size, baseline_rate, power=0.8, significance_level=0.05):
    """
    Calculate the Minimum Detectable Effect (relative) for a fixed sample size.
    Uses binary search to find the smallest effect size that achieves the desired power.
    """
    max_effect = (1.0 - baseline_rate) / baseline_rate
    left, right = 1e-9, min(1.0, max_effect) * (1 - 1e-12)
    while right - left > 1e-6:
        mid = (left + right) / 2
        if two_proportion_power(mid, sample_size, baseline_rate, significance_level) < power:
            left = mid
        else:
            right = mid
    return (left + right) / 2


def calculate_required_sample_size(mde, baseline_rate, power=0.8, significance_level=0.05):
    """
    Calculate required sample size per variation for a relative MDE.
    Uses binary search to find the smallest sample size that achieves the desired power.
    """
    left, right = 1, 1_000_000_000
    while right - left > 1:
        mid = (left + right) // 2
        if two_proportion_power(mde, mid, baseline_rate, significance_level) < power:
            left = mid
        else:
            right = mid
    return right


def evaluate_test(traffic_control, conversions_control, traffic_variant, conversions_variant,
                  significance_level=0.05, two_sided=True, alternative="greater"):
    """Evaluate an A/B test and return rates, errors, test statistic and p-value.

    For a one-sided test, ``alternative`` selects the pre-specified direction:
    "greater" tests H1: variant rate > control rate, "less" tests the opposite.
    """
    cvr_control = conversions_control / traffic_control
    cvr_variant = conversions_variant / traffic_variant
    uplift = ((cvr_variant - cvr_control) / cvr_control) if cvr_control != 0 else 0.0

    se_control = np.sqrt(cvr_control * (1 - cvr_control) / traffic_control)
    se_variant = np.sqrt(cvr_variant * (1 - cvr_variant) / traffic_variant)
    se_diff = np.sqrt(se_control ** 2 + se_variant ** 2)
    z_score = (cvr_variant - cvr_control) / se_diff if se_diff != 0 else 0.0

    if two_sided:
        p_value = 2 * (1 - stats.norm.cdf(abs(z_score)))
    elif alternative == "less":
        p_value = stats.norm.cdf(z_score)
    else:
        p_value = 1 - stats.norm.cdf(z_score)

    critical_value = significance_to_z(significance_level, two_sided)
    ci_z = significance_to_z(significance_level, two_sided)

    return {
        "cvr_control": cvr_control,
        "cvr_variant": cvr_variant,
        "uplift": uplift,
        "se_control": se_control,
        "se_variant": se_variant,
        "se_diff": se_diff,
        "z_score": z_score,
        "p_value": p_value,
        "critical_value": critical_value,
        "significant": p_value < significance_level,
        "ci_control": ci_z * se_control,
        "ci_variant": ci_z * se_variant,
    }

def main():
    st.set_page_config(page_title="Multi-Mode A/B Test Calculator", layout="wide")
    
    st.title("Multi-Mode A/B Test Calculator")
    with st.expander("Made by [apprtm-nft](mailto:agung.pprtm@gmail.com). Read More", expanded=False):
        st.markdown("""            
        This calculator helps you with two different analyses:
        
        - **Pre-Test Analysis:** Calculate your Minimum Detectable Effect (MDE) or required sample size based on your baseline conversion rate.
        - **Test Evaluation:** Evaluate your A/B test results by comparing the conversion rates of your control and variant groups.
        """)
    
    # Select analysis type
    analysis_type = st.selectbox(
        "Select Analysis Type:",
        options=["Pre-Test Analysis", "Test Evaluation"],
        help="Choose whether you want to set up your test parameters or evaluate your test results."
    )
    
    if analysis_type == "Pre-Test Analysis":
        # --- Existing Pre-Test Analysis (MDE and sample size calculator) ---
        st.markdown("### Calculator Mode")
        mode = st.radio(
            "Select Calculator Mode:",
            ["Calculate from sample size", "Calculate from total population"],
            horizontal=True,
            help="Choose whether to start with sample size per variation or total population"
        )
        
        # Common parameters for both modes
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
            "Alpha/Confidence Level (α):",
            min_value=0.01,
            max_value=0.10,
            value=0.05,
            format="%0.2f",
            help="Alpha level (e.g., 0.05 for 95% confidence level)"
        )
        
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
                    "Or set desired MDE (%) (Optional):",
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
            - Total samples needed: {sample_size*2:,} (across 2 variations, A/B)
            
            **With desired MDE of ±{user_mde*100:.1f}%:**
            - You would need {required_sample_size:,} samples per variation
            - Total samples needed: {required_sample_size*2:,} (across 2 variations, A/B)
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
    
        # Power Analysis section
        st.markdown("---")
        st.subheader("Power Analysis")
        
        # Create power curve with both positive and negative effects
        max_effect = max(mde * 3, user_mde * 3) if abs(user_mde - mde) > 0.0001 else mde * 3
        effect_sizes = np.linspace(-max_effect, max_effect, 200)
        powers = [
            two_proportion_power(effect, sample_size, baseline_rate, significance, two_sided=True)
            for effect in effect_sizes
        ]
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=effect_sizes*100,
            y=powers,
            mode='lines',
            name='Power Curve',
            hovertemplate='Effect Size: %{x:.1f}%<br>Power: %{y:.1%}<extra></extra>'
        ))
        fig.add_hline(y=power, line_dash="dash", line_color="red",
                     annotation_text=f"Target Power ({power:.0%})")
        fig.add_vline(x=mde*100, line_dash="dash", line_color="green",
                     annotation_text=f"+MDE ({mde*100:.1f}%)")
        fig.add_vline(x=-mde*100, line_dash="dash", line_color="green",
                     annotation_text=f"-MDE ({mde*100:.1f}%)")
        if abs(user_mde - mde) > 0.0001:
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
                x=(-max_effect*100 - mde*100)/2,
                y=0.95,
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
                x=(max_effect*100 + mde*100)/2,
                y=0.85,
                showarrow=False,
                yref='paper',
                xref='x'
            )
        )
        
        fig.update_layout(
            title="Statistical Power vs Effect Size",
            xaxis_title="Effect Size (%)",
            yaxis_title="Statistical Power",
            height=500,
            showlegend=True,
            xaxis=dict(
                range=[-max_effect*100, max_effect*100],
                tickformat='.1f',
                ticksuffix='%'
            ),
            yaxis=dict(
                range=[0, 1],
                tickformat='.0%'
            ),
            margin=dict(t=50, b=50, l=50, r=50),
            hovermode='x unified'
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    else:
        # --- Test Evaluation Section ---
        st.markdown("### Test Evaluation")
        st.markdown("Enter the traffic and conversion numbers for your control and variant groups:")
        col_control, col_variant = st.columns(2)
        with col_control:
            traffic_control = st.number_input(
                "Control Traffic:",
                min_value=1,
                value=1000,
                step=1,
                help="Number of users in the control group"
            )
            conv_control = st.number_input(
                "Control Conversions:",
                min_value=0,
                value=300,
                step=1,
                help="Number of conversions in the control group"
            )
        with col_variant:
            traffic_variant = st.number_input(
                "Variant Traffic:",
                min_value=1,
                value=1000,
                step=1,
                help="Number of users in the variant group"
            )
            conv_variant = st.number_input(
                "Variant Conversions:",
                min_value=0,
                value=350,
                step=1,
                help="Number of conversions in the variant group"
            )
        
        st.markdown("#### Test Parameters")
        test_type = st.radio(
            "Select Test Type:",
            options=["One-Tailed", "Two-Tailed"],
            horizontal=True,
            help="Choose one-tailed if you have a directional hypothesis (e.g., variant is expected to be higher) or two-tailed for a non-directional hypothesis"
        )
        if test_type == "One-Tailed":
            direction = st.radio(
                "Expected Direction:",
                options=["Variant is higher than control", "Variant is lower than control"],
                horizontal=True,
                help="The pre-specified direction of your one-tailed hypothesis"
            )
        else:
            direction = "Variant is higher than control"
        confidence_option = st.selectbox(
            "Select Confidence Level:",
            options=["90%", "95%", "99%"],
            index=1,
            help="Select the confidence level for your test (default is 95%)"
        )
        confidence = float(confidence_option.strip('%')) / 100.0
        significance = 1 - confidence
        
        if traffic_control > 0 and traffic_variant > 0:
            if conv_control > traffic_control or conv_variant > traffic_variant:
                st.error("Conversions cannot exceed traffic for either group.")
                st.stop()

            two_sided = test_type == "Two-Tailed"
            alternative = "greater" if direction == "Variant is higher than control" else "less"

            result = evaluate_test(
                traffic_control, conv_control, traffic_variant, conv_variant,
                significance_level=significance, two_sided=two_sided, alternative=alternative,
            )
            cvr_control = result["cvr_control"]
            cvr_variant = result["cvr_variant"]
            uplift = result["uplift"] * 100
            se_control = result["se_control"]
            se_variant = result["se_variant"]
            se_diff = result["se_diff"]
            z_score = result["z_score"]
            p_value = result["p_value"]
            critical_value = result["critical_value"]
            significant = result["significant"]

            observed_power = 1 - stats.norm.cdf(critical_value - abs(z_score))
            relative_diff = ((cvr_variant - cvr_control) / cvr_control * 100) if cvr_control != 0 else 0.0

            # Prepare a descriptive message in a highlighted box.
            if significant:
                direction_word = "higher" if relative_diff >= 0 else "lower"
                result_message = (
                    f"**Significant test result!**\n\n"
                    f"Variation B's observed conversion rate ({cvr_variant*100:.2f}%) was "
                    f"{abs(relative_diff):.2f}% {direction_word} than variation A's conversion rate ({cvr_control*100:.2f}%).\n\n"
                    f"You can be {confidence_option} confident that this result is due to the changes you made and not random chance."
                )
                result_box = st.success
            else:
                result_message = (
                    f"**Not significant.**\n\n"
                    f"Variation B's observed conversion rate ({cvr_variant*100:.2f}%) was "
                    f"{relative_diff:+.2f}% different from variation A's conversion rate ({cvr_control*100:.2f}%).\n\n"
                    f"This difference is not statistically significant at the {confidence_option} confidence level."
                )
                result_box = st.warning
            
            # Show result overview box on top
            result_box(result_message)
            
            # Add plot type selector
            plot_type = st.radio(
                "Select Visualization Type:",
                ["Box Plot", "Probability Density"],
                horizontal=True,
                help="Choose how to visualize the test results"
            )
            
            if plot_type == "Box Plot":
                # Original box plot code
                fig = go.Figure()
                # Calculate z-value based on selected confidence level
                if test_type == "One-Tailed":
                    z_val = stats.norm.ppf(confidence)  # One-tailed z-value
                else:
                    z_val = stats.norm.ppf(1 - (1 - confidence) / 2)  # Two-tailed z-value
                ci_control = z_val * se_control
                ci_variant = z_val * se_variant

                # Plot the control and variant points with error bars
                fig.add_trace(go.Scatter(
                    x=["Control"],
                    y=[cvr_control*100],
                    mode="markers",
                    marker=dict(size=12, color="blue"),
                    error_y=dict(
                        type="data",
                        array=[ci_control*100],
                        visible=True,
                        thickness=1.5,
                        color="blue"
                    ),
                    name="Control"
                ))
                fig.add_trace(go.Scatter(
                    x=["Variant"],
                    y=[cvr_variant*100],
                    mode="markers",
                    marker=dict(size=12, color="orange"),
                    error_y=dict(
                        type="data",
                        array=[ci_variant*100],
                        visible=True,
                        thickness=1.5,
                        color="orange"
                    ),
                    name="Variant"
                ))
                
                # Add annotation for CI overlap
                if (cvr_control + ci_control) < (cvr_variant - ci_variant):
                    annotation_text = f"{int(confidence*100)}% CIs do not overlap"
                elif (cvr_variant + ci_variant) < (cvr_control - ci_control):
                    annotation_text = f"{int(confidence*100)}% CIs do not overlap"
                else:
                    annotation_text = f"{int(confidence*100)}% CIs overlap"
                
                # Draw horizontal lines for the upper bound of the lower group and lower bound of the higher group
                if cvr_control < cvr_variant:
                    lower_group_upper = (cvr_control + ci_control)*100
                    higher_group_lower = (cvr_variant - ci_variant)*100
                    upper_bound_label = "Upper Bound of Control CI"
                    lower_bound_label = "Lower Bound of Variant CI"
                    upper_bound_color = "rgba(0, 0, 255, 0.7)"  # Blue for Control
                    lower_bound_color = "rgba(255, 165, 0, 0.7)"  # Orange for Variant
                else:
                    lower_group_upper = (cvr_variant + ci_variant)*100
                    higher_group_lower = (cvr_control - ci_control)*100
                    upper_bound_label = "Upper Bound of Variant CI"
                    lower_bound_label = "Lower Bound of Control CI"
                    upper_bound_color = "rgba(255, 165, 0, 0.7)"  # Orange for Variant
                    lower_bound_color = "rgba(0, 0, 255, 0.7)"  # Blue for Control
                
                # Add horizontal lines with more prominent annotations
                fig.add_hline(
                    y=lower_group_upper,
                    line_dash="dot",
                    line_color=upper_bound_color,
                    line_width=2
                )
                fig.add_hline(
                    y=higher_group_lower,
                    line_dash="dot",
                    line_color=lower_bound_color,
                    line_width=2
                )
                
                # Add annotations with better visibility
                annotations = [
                    # Overlap status annotation
                    dict(
                        x=0.5,
                        y=max(cvr_control, cvr_variant)*100 + 3,
                        xref="paper",
                        yref="y",
                        text=annotation_text,
                        showarrow=False,
                        font=dict(size=12)
                    ),
                    # Lower bound annotation
                    dict(
                        x=0,
                        y=lower_group_upper,
                        xref="paper",
                        yref="y",
                        text=upper_bound_label,
                        showarrow=True,
                        arrowhead=2,
                        arrowsize=1,
                        arrowwidth=2,
                        arrowcolor=upper_bound_color,
                        ax=70,
                        ay=0,
                        font=dict(size=11, color=upper_bound_color),
                        bgcolor="rgba(255, 255, 255, 0.8)",
                        bordercolor=upper_bound_color,
                        borderwidth=1,
                        borderpad=4,
                        xanchor="right"
                    ),
                    # Upper bound annotation
                    dict(
                        x=0,
                        y=higher_group_lower,
                        xref="paper",
                        yref="y",
                        text=lower_bound_label,
                        showarrow=True,
                        arrowhead=2,
                        arrowsize=1,
                        arrowwidth=2,
                        arrowcolor=lower_bound_color,
                        ax=70,
                        ay=0,
                        font=dict(size=11, color=lower_bound_color),
                        bgcolor="rgba(255, 255, 255, 0.8)",
                        bordercolor=lower_bound_color,
                        borderwidth=1,
                        borderpad=4,
                        xanchor="right"
                    )
                ]
                
                fig.update_layout(
                    title=f"Control vs Variant Conversion Rates with {int(confidence*100)}% CI",
                    yaxis_title="Conversion Rate (%)",
                    xaxis_title="Group",
                    yaxis=dict(tickformat=".2f"),
                    annotations=annotations,
                    margin=dict(l=150, r=50, t=50, b=50),
                    showlegend=True,
                    plot_bgcolor="white"
                )
            
            else:  # Probability Density plot
                # Generate x values for the normal distributions
                x = np.linspace(
                    min(cvr_control - 4*se_control, cvr_variant - 4*se_variant),
                    max(cvr_control + 4*se_control, cvr_variant + 4*se_variant),
                    1000
                )
                
                # Calculate normal distributions
                y_control = stats.norm.pdf(x, cvr_control, se_control)
                y_variant = stats.norm.pdf(x, cvr_variant, se_variant)
                
                # Scale the distributions for better visualization
                max_height = max(max(y_control), max(y_variant))
                y_control = (y_control / max_height) * 30  # Scale to max height of 30
                y_variant = (y_variant / max_height) * 30
                
                # Create the plot
                fig = go.Figure()
                
                # Add vertical lines for confidence intervals
                if test_type == "One-Tailed":
                    z_val = stats.norm.ppf(confidence)  # One-tailed z-value
                else:
                    z_val = stats.norm.ppf(1 - (1 - confidence) / 2)  # Two-tailed z-value
                ci_lower_control = (cvr_control - z_val*se_control)*100
                ci_upper_control = (cvr_control + z_val*se_control)*100
                
                # Add the distributions with colored fills for areas outside CI
                # Only add colored fills if the result is significant
                if significant:  # Only show fills for significant results
                    if test_type == "One-Tailed":
                        if z_score >= 0:  # Testing for improvement
                            # Create a trace for the area above CI (green)
                            mask_above = np.where(x*100 > ci_upper_control, y_variant, 0)
                            fig.add_trace(go.Scatter(
                                x=x*100,
                                y=mask_above,
                                fill='tozeroy',
                                fillcolor="rgba(200, 255, 200, 0.5)",  # Green
                                line=dict(width=0),
                                showlegend=False,
                                hoverinfo='skip'
                            ))
                        else:  # Testing for degradation
                            # Create a trace for the area below CI (red)
                            mask_below = np.where(x*100 < ci_lower_control, y_variant, 0)
                            fig.add_trace(go.Scatter(
                                x=x*100,
                                y=mask_below,
                                fill='tozeroy',
                                fillcolor="rgba(255, 200, 200, 0.5)",  # Red
                                line=dict(width=0),
                                showlegend=False,
                                hoverinfo='skip'
                            ))
                    else:  # Two-tailed test
                        fill_color = "rgba(255, 200, 200, 0.5)" if cvr_variant < cvr_control else "rgba(200, 255, 200, 0.5)"
                        # Create traces for areas outside CI
                        mask_outside = np.where((x*100 < ci_lower_control) | (x*100 > ci_upper_control), y_variant, 0)
                        fig.add_trace(go.Scatter(
                            x=x*100,
                            y=mask_outside,
                            fill='tozeroy',
                            fillcolor=fill_color,
                            line=dict(width=0),
                            showlegend=False,
                            hoverinfo='skip'
                        ))
                
                # Add the main variant distribution curve (without fill)
                fig.add_trace(go.Scatter(
                    x=x*100,
                    y=y_variant,
                    line=dict(color='orange'),
                    name='Variant B',
                    hovertemplate='CR: %{x:.2f}%<br>Density: %{y:.2f}<extra></extra>'
                ))
                
                # Add control distribution
                fig.add_trace(go.Scatter(
                    x=x*100,
                    y=y_control,
                    line=dict(color='blue'),
                    name='Control A',
                    hovertemplate='CR: %{x:.2f}%<br>Density: %{y:.2f}<extra></extra>'
                ))
                
                # Add vertical lines for the means
                fig.add_vline(x=cvr_control*100, line_dash="solid", line_color="blue",
                            annotation_text=f"CR A: {cvr_control*100:.2f}%")
                fig.add_vline(x=cvr_variant*100, line_dash="solid", line_color="orange",
                            annotation_text=f"CR B: {cvr_variant*100:.2f}%")
                
                # Add confidence interval lines based on test type
                if test_type == "One-Tailed":
                    # For one-tailed test, only show the relevant boundary
                    if z_score >= 0:  # Testing for improvement
                        fig.add_vline(x=ci_upper_control, line_dash="dash", line_color="blue",
                                    annotation_text=f"{(1-significance)*100:.0f}%")
                    else:  # Testing for degradation
                        fig.add_vline(x=ci_lower_control, line_dash="dash", line_color="blue",
                                    annotation_text=f"{(1-significance)*100:.0f}%")
                else:  # Two-tailed test
                    # Show both boundaries for two-tailed test
                    fig.add_vline(x=ci_lower_control, line_dash="dash", line_color="blue",
                                annotation_text=f"{(1-significance)*100:.0f}%")
                    fig.add_vline(x=ci_upper_control, line_dash="dash", line_color="blue",
                                annotation_text=f"{(1-significance)*100:.0f}%")
                
                fig.update_layout(
                    title="The expected distributions of variation A and B",
                    xaxis_title="Conversion Rate (%)",
                    yaxis_title="Density",
                    showlegend=True,
                    xaxis=dict(tickformat='.2f'),
                    hovermode='x unified'
                )
            
            st.plotly_chart(fig, use_container_width=True)
            if plot_type == "Box Plot":
                st.caption(
                    "Note: overlapping confidence intervals do not by themselves imply a "
                    "non-significant difference; the significance verdict is based on the p-value."
                )
            
            # -------------------------------
            # 3. Show evaluation results in three rows of three columns each.
            # -------------------------------
            st.markdown("#### Detailed Test Evaluation Results")
            
            # Row 1: Conversion Rates and Uplift
            col1, col2, col3 = st.columns(3)
            with col1:
                st.markdown("**Conversion Rate A**")
                st.markdown(f"""
                <div style='background-color: #f5f5f5; padding: 10px; border-radius: 5px; margin-bottom: 25px;'>
                    {cvr_control*100:.2f}%
                </div>
                """, unsafe_allow_html=True)

            with col2:
                st.markdown("**Conversion Rate B**")
                st.markdown(f"""
                <div style='background-color: #f5f5f5; padding: 10px; border-radius: 5px; margin-bottom: 25px;'>
                    {cvr_variant*100:.2f}%
                </div>
                """, unsafe_allow_html=True)

            with col3:
                st.markdown("**Relative uplift in Conversion Rate**")
                bg_color = "#e8f5e9" if uplift > 0 else "#ffebee"  # Green if positive, red if negative
                st.markdown(f"""
                <div style='background-color: {bg_color}; padding: 10px; border-radius: 5px; margin-bottom: 25px;'>
                    {uplift:.2f}%
                </div>
                """, unsafe_allow_html=True)
            
            # Row 2: Power, p-value, Z-score
            col4, col5, col6 = st.columns(3)
            with col4:
                st.markdown("**Post-hoc Power (observed)**")
                st.markdown(f"""
                <div style='background-color: #f5f5f5; padding: 10px; border-radius: 5px; margin-bottom: 25px;'>
                    {observed_power*100:.2f}%
                </div>
                """, unsafe_allow_html=True)

            with col5:
                st.markdown("**p-value**")
                st.markdown(f"""
                <div style='background-color: #f5f5f5; padding: 10px; border-radius: 5px; margin-bottom: 25px;'>
                    {p_value:.4f}
                </div>
                """, unsafe_allow_html=True)

            with col6:
                st.markdown("**Z-score**")
                st.markdown(f"""
                <div style='background-color: #f5f5f5; padding: 10px; border-radius: 5px; margin-bottom: 25px;'>
                    {z_score:.4f}
                </div>
                """, unsafe_allow_html=True)
            st.caption(
                "Post-hoc power is derived from the observed effect and is reported for "
                "completeness only; it is not a substitute for a priori power planning."
            )
            
            # Row 3: Standard Errors
            col7, col8, col9 = st.columns(3)
            with col7:
                st.markdown("**Standard error A**")
                st.markdown(f"""
                <div style='background-color: #f5f5f5; padding: 10px; border-radius: 5px; margin-bottom: 25px;'>
                    {se_control:.5f}
                </div>
                """, unsafe_allow_html=True)

            with col8:
                st.markdown("**Standard error B**")
                st.markdown(f"""
                <div style='background-color: #f5f5f5; padding: 10px; border-radius: 5px; margin-bottom: 25px;'>
                    {se_variant:.5f}
                </div>
                """, unsafe_allow_html=True)

            with col9:
                st.markdown("**Std. Error of difference**")
                st.markdown(f"""
                <div style='background-color: #f5f5f5; padding: 10px; border-radius: 5px; margin-bottom: 25px;'>
                    {se_diff:.5f}
                </div>
                """, unsafe_allow_html=True)
        else:
            st.error("Traffic values must be greater than 0 for both control and variant groups.")

if __name__ == "__main__":
    main()
