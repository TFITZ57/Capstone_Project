import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

# Constants for BUY and SELL signals
BUY_SIGNAL = 1
SELL_SIGNAL = 2
HOLD_SIGNAL = 0

def generate_labels(df, threshold=0.01, close_col='close'):
    df['labels'] = HOLD_SIGNAL
    df['Price Change'] = df[close_col].pct_change()

    df.loc[df['Price Change'] > threshold, 'labels'] = BUY_SIGNAL
    df.loc[df['Price Change'] < -threshold, 'labels'] = SELL_SIGNAL

    return df

def strat_1(df, stop_loss_threshold, transaction_fee, close_col='close', low_col='low'):
    df['time'] = pd.to_datetime(df['time'])
    df = df.drop_duplicates(subset='time')
    df.set_index('time', inplace=True)
    df.info()  # Print DataFrame info to check structure and data types

    if not isinstance(df, pd.DataFrame):
        raise TypeError("The input 'df' must be a pandas DataFrame")

    if 'labels' not in df.columns:
        raise KeyError("The DataFrame does not contain the 'labels' column")

    pending_order = False
    entry_price = 0
    total_capital = 1
    capital_history = []

    max_drawdown = 0
    max_profit = 0
    operation_count = 0
    profitable_operations = 0

    for index, row in df.iterrows():
        capital_history.append(total_capital)
        print(f"Processing row: {index}, Label: {row['labels']}")  # Debug print for each row

        # Handle stop loss
        if pending_order:
            exit_price = row[low_col]
            percent_change = (exit_price - entry_price) / entry_price
            if percent_change < -stop_loss_threshold:
                print(f"Stop loss triggered at {exit_price} on {index}")
                pending_order = False
                exit_price = entry_price * (1 - stop_loss_threshold)
                percent_change = (exit_price - entry_price) / entry_price

                if percent_change < max_drawdown:
                    max_drawdown = percent_change

                total_capital *= 1 + (((exit_price * (1 - transaction_fee)) - (entry_price * (1 + transaction_fee))) / (entry_price * (1 + transaction_fee)))
                entry_price = 0

        # Issue BUY order
        if row['labels'] == BUY_SIGNAL:
            if pending_order:
                continue
            else:
                pending_order = True
                entry_price = row[close_col]
                operation_count += 1
                print(f"BUY at {entry_price} on {index}")  # Debug print for BUY order
                continue

        # Close order if SELL
        if row['labels'] == SELL_SIGNAL:
            if pending_order:
                exit_price = row[close_col]
                percent_change = (exit_price - entry_price) / entry_price
                if percent_change > 0:
                    profitable_operations += 1

                if percent_change < max_drawdown:
                    max_drawdown = percent_change

                if percent_change > max_profit:
                    max_profit = percent_change

                pending_order = False
                total_capital *= 1 + (((exit_price * (1 - transaction_fee)) - (entry_price * (1 + transaction_fee))) / (entry_price * (1 + transaction_fee)))
                print(f"SELL at {exit_price} on {index}")  # Debug print for SELL order
                entry_price = 0

    # Handle last candle
    if pending_order:
        exit_price = df.iloc[-1][low_col]
        percent_change = (exit_price - entry_price) / entry_price
        if percent_change < -stop_loss_threshold:
            exit_price = entry_price * (1 - stop_loss_threshold)

        if percent_change < max_drawdown:
            max_drawdown = percent_change

        if percent_change > max_profit:
            max_profit = percent_change

        total_capital *= 1 + (((exit_price * (1 - transaction_fee)) - (entry_price * (1 + transaction_fee))) / (entry_price * (1 + transaction_fee)))

    # Ensure returns series is not empty
    if len(capital_history) > 1:
        returns = pd.Series(np.diff(capital_history) / capital_history[:-1], index=df.index[1:])
        returns = pd.Series(returns, index=pd.to_datetime(df.index))
    else:
        returns = pd.Series([], dtype=float)

    print(f"Total capital: {total_capital}")
    print(f"Operation count: {operation_count}")
    print(f"Profitable operations: {profitable_operations}")
    print(f"Max drawdown: {max_drawdown}")
    print(f"Max profit: {max_profit}")
    print(f"Capital history: {capital_history}")  # Debug print for capital history
    print(f"Returns: {returns}")  # Debug print for returns

    return capital_history, total_capital, operation_count, max_drawdown, max_profit, profitable_operations, returns

# Streamlit app
def load_data():
    # Replace with the path to your CSV file
    return pd.read_csv('crypto_dataset.csv')

def main():
    st.title("Cryptocurrency Price Prediction and Trading Strategy Simulation")
    st.write("This application visualizes predictions from a machine learning model trained on cryptocurrency data and simulates a trading strategy.")

    data = load_data()
    st.subheader("Cryptocurrency Data")
    st.write(data.head())
    st.write(data.columns)  # Display columns to identify correct names

    # Detect columns names for 'close' and 'low' prices
    if 'close' not in data.columns or 'low' not in data.columns:
        st.error("The dataset must contain 'close' and 'low' columns.")
        return

    # Generate labels based on price change
    data = generate_labels(data, close_col='close')

    stop_loss_threshold = st.sidebar.slider('Stop Loss Threshold', min_value=0.01, max_value=0.10, value=0.02, step=0.01)
    transaction_fee = st.sidebar.slider('Transaction Fee', min_value=0.000, max_value=0.010, value=0.001, step=0.001)

    if st.button('Run Trading Strategy'):
        try:
            history, final_capital, num_ops, min_dd, max_gain, good_ops, returns = strat_1(data, stop_loss_threshold, transaction_fee, close_col='close', low_col='low')

            st.subheader("Trading Strategy Results")
            st.write(f"Final Capital: {final_capital}")
            st.write(f"Total Operations: {num_ops}")
            st.write(f"Profitable Operations: {good_ops}")
            st.write(f"Max Drawdown: {min_dd}")
            st.write(f"Max Profit: {max_gain}")

            st.subheader("Capital History")
            plt.figure(figsize=(10, 5))
            plt.plot(history, label='Capital Over Time')
            plt.xlabel('Time')
            plt.ylabel('Capital')
            plt.legend()
            st.pyplot(plt)

            st.subheader("Returns Over Time")
            plt.figure(figsize=(10, 5))
            plt.plot(returns, label='Returns')
            plt.xlabel('Time')
            plt.ylabel('Returns')
            plt.legend()
            st.pyplot(plt)

        except KeyError as e:
            st.error(f"KeyError: {e}. Please ensure your data contains the required columns.")

    # List of plots
    plots = {
        "Balanced": "plots/class_distributions_balanced.png",
        "Initial": "plots/class_distributions_initial.png",
        "Calibration Curve": "plots/hyperband_1_calibration_curve.png",
        "Class Accuracy": "plots/hyperband_1_class_accuracy.png",
        "Label Distribution": "plots/label_distribution.png",
        "Confusion Matrix": "plots/hyperband_1_confusion_matrix.png",
        "Precision Recall Curve": "plots/hyperband_1_precision_recall_curve.png",
        "ROC Curve": "plots/hyperband_1_roc_curve.png",
        "Training Accuracy": "plots/hyperband_1_training_accuracy_loss.png",
        "Training Accuracy (Screenshot)": "plots/Screenshot 2024-06-12 at 1.07.39 AM.png",
        "Model Graph": "plots/model_graph.png",
        "Random Search Calibration Curve": "plots/randomsearch_1_calibration_curve.png",
        "Random Search Class Accuracy": "plots/randomsearch_1_class_accuracy.png",
        "Random Search Confusion Matrix": "plots/randomsearch_1_confusion_matrix.png",
        "Random Search Precision Recall Curve": "plots/randomsearch_1_precision_recall_curve.png",
        "Random Search ROC Curve": "plots/randomsearch_1_roc_curve.png",
        "Random Search Training Accuracy Loss": "plots/randomsearch_1_training_accuracy_loss.png",
    }


    # Dropdown menu to select the plot
    st.subheader("Model Evaluation Plots")
    plot_choice = st.selectbox("Choose a plot to display:", list(plots.keys()))

    # Display the selected plot
    st.image(plots[plot_choice], caption=f"Plot: {plot_choice}", use_column_width=True)

if __name__ == "__main__":
    main()