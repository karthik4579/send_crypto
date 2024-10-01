import streamlit as st
from manage import get_wallets, send_crypto, get_wallet_balance

def send_crypto_page():
    st.title("Send Crypto (Only Ethereum supported currently)")

    wallets = get_wallets()
    # Filter out Dash wallets
    non_dash_wallets = [wallet for wallet in wallets if wallet['type'].lower() != 'dash']
    wallet_names = [wallet['name'] for wallet in non_dash_wallets]
    
    if not wallet_names:
        st.warning("No supported wallets found. Please create a Bitcoin or Ethereum wallet first.")
        return

    selected_wallet = st.selectbox("Select Wallet", wallet_names)
    
    # Retrieve the selected wallet's details
    wallet = next((w for w in non_dash_wallets if w['name'] == selected_wallet), None)
    
    if wallet:
        to_address = st.text_input("Recipient Address")
        amount = st.number_input("Amount to send", min_value=0.0, format="%.8f", step=0.0001)
    
        if st.button("Send Transaction"):
            if to_address and amount > 0:
                result = send_crypto(wallet, to_address, amount, wallet['type'])
                if isinstance(result, dict):
                    if 'txid' in result and result['status'] == 'success':
                        st.success("Transaction sent successfully!")
                        st.markdown(f"**Transaction ID:** `{result['txid']}`")
                        st.markdown(f"**Status:** {result['status'].capitalize()}")
                    elif 'error' in result:
                        st.error(f"Failed to send transaction: {result['error']}")
                    else:
                        st.error(f"Unexpected result format: {result}")
                else:
                    st.error(f"Failed to send transaction: {result}")
            else:
                st.warning("Please fill in all fields correctly.")
    else:
        st.error("Selected wallet not found.")

if __name__ == "__main__":
    send_crypto_page()