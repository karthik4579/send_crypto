import streamlit as st
import manage
import os
from dotenv import load_dotenv
import base64  # Add this import
import pandas as pd  # Add this import
from send_crypto import send_crypto_page  # Import the send_crypto_page

# Load environment variables
load_dotenv('config.env')

def main():
    st.set_page_config(page_title="Wallet Manager", layout="wide")
    
    # Add CSS to position the logo
    st.markdown(
        """
        <style>
        .logo-img {
            position: absolute;
            top: 10px;
            right: 10px;
            width: 100px;
        }
        </style>
        """,
        unsafe_allow_html=True
    )
    
    # Display logo
    st.markdown(
        """
        <img src="data:image/png;base64,{}" class="logo-img">
        """.format(
            base64.b64encode(open("logo.png", "rb").read()).decode()
        ),
        unsafe_allow_html=True
    )

    if 'page' not in st.session_state:
        st.session_state.page = 'dashboard'

    if st.session_state.page == 'dashboard':
        show_dashboard()
    elif st.session_state.page == 'manage_wallets':
        show_manage_wallets()
    elif st.session_state.page == 'send_crypto':
        send_crypto_page()  # Display the send crypto page

def show_dashboard():
    st.title("Wallet Manager Dashboard")
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("Manage Wallets"):
            st.session_state.page = 'manage_wallets'
            st.rerun()
    
    with col2:
        if st.button("Send Crypto"):
            st.session_state.page = 'send_crypto'
            st.rerun()

def show_manage_wallets():
    st.title("Manage Wallets")
    
    # Back button
    if st.button("← Back to Dashboard", key="back_button"):
        st.session_state.page = 'dashboard'
        st.rerun()
    
    # Create wallet section
    st.header("Create New Wallet")
    
    # Use a form for wallet creation
    with st.form(key='create_wallet_form'):
        wallet_name = st.text_input("Wallet Name")
        wallet_password = st.text_input("Wallet Password", type="password")
        wallet_type = st.selectbox("Cryptocurrency", ["Bitcoin", "Dash", "Ethereum"])
        submit_button = st.form_submit_button(label='Create Wallet')

    if submit_button:
        result = manage.create_wallet(wallet_name, wallet_password, wallet_type)
        if isinstance(result, dict) and 'private_key' in result:
            st.success(f"Wallet '{wallet_name}' created successfully!")
            st.warning("Please store your private key safely:")
            st.code(result['private_key'])
            # Clear the form fields in session state
            st.session_state.wallet_name = ""
            st.session_state.wallet_password = ""
            st.session_state.wallet_type = "Bitcoin"
        else:
            st.error(f"Failed to create wallet: {result}")

    # List existing wallets
    st.header("Your Wallets")
    wallets = manage.get_wallets()
    for wallet in wallets:
        with st.expander(f"{wallet['name']} ({wallet['type']})"):
            st.write(f"Address: {wallet['address']}")
            balance = manage.get_wallet_balance(wallet['address'], wallet['type'])
            
            if isinstance(balance, dict):
                st.write(f"Total Balance: {balance['total']} {balance['unit']}")
            else:
                st.write(f"Balance: {balance}")  # In case of an error message
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("View Transaction History", key=f"history_{wallet['address']}"):
                    history = manage.get_transaction_history(wallet['address'], wallet['type'])
                    if isinstance(history, list):
                        if not history:
                            st.info("No transactions found for this wallet.")
                        else:
                            processed_transactions = []
                            for tx in history:
                                processed_tx = {
                                    'index': tx.get('index'),
                                    'minedInBlockHash': tx.get('minedInBlockHash'),
                                    'minedInBlockHeight': tx.get('minedInBlockHeight'),
                                    'recipients': ', '.join([r.get('address', '') for r in tx.get('recipients', [])]),
                                    'senders': ', '.join([s.get('address', '') for s in tx.get('senders', [])]),
                                    'timestamp': tx.get('timestamp'),
                                    'transactionHash': tx.get('transactionHash')
                                }
                                processed_transactions.append(processed_tx)
                            
                            df = pd.DataFrame(processed_transactions)
                            st.dataframe(df)
                    else:
                        st.error(f"Error fetching transaction history: {history}")

            with col2:
                if st.button("Delete Wallet", key=f"delete_{wallet['address']}"):
                    if manage.delete_wallet(wallet['name'], wallet['type'], wallet['address']):
                        st.success(f"Wallet '{wallet['name']}' deleted successfully!")
                        st.rerun()
                    else:
                        st.error("Failed to delete wallet.")

if __name__ == "__main__":
    main()