import streamlit as st
import importlib
import sys
from pathlib import Path
import os
from dotenv import load_dotenv

load_dotenv()  # Load .env for API configs if used

# Add current directory to path
sys.path.append(str(Path(__file__).parent))

# ==================== Page Configuration ====================
st.set_page_config(
    page_title="Fleet Management System",
    page_icon="🚛",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        'About': """
        Fleet Management System v3.0
        
        A comprehensive fleet management solution with:
        - Real-time vehicle tracking
        - Repair order management
        - Analytics and reporting
        - Cost analysis
        
        Built with Streamlit & Python
        """
    }
)

# ==================== Session State ====================
def init_session_state():
    """Initialize session state variables"""
    if 'current_page' not in st.session_state:
        st.session_state.current_page = 'Dashboard'
    if 'samsara_token' not in st.session_state:
        st.session_state.samsara_token = ''
    if 'fleetrock_api_key' not in st.session_state:
        st.session_state.fleetrock_api_key = ''
    if 'fleetrock_username' not in st.session_state:
        st.session_state.fleetrock_username = os.getenv('FLEETROCK_USERNAME', 'wanship.shop')
    if 'fleetrock_base_url' not in st.session_state:
        st.session_state.fleetrock_base_url = os.getenv('FLEETROCK_BASE_URL', 'https://loves.fleetrock.com/API')

init_session_state()

# ==================== Navigation ====================
def main():
    """Main application with navigation"""
    
    # Sidebar navigation
    with st.sidebar:
        st.title("🚛 Fleet Management")
        st.markdown("---")
        
        # Navigation menu
        st.markdown("### 🧭 Navigation")
        page = st.radio(
            "Select Module",
            ["Dashboard", "Repair Orders"],
            index=0 if st.session_state.current_page == "Dashboard" else 1,
            label_visibility="collapsed"
        )
        
        st.session_state.current_page = page
        
        # Divider
        st.markdown("---")
        
        # System info
        st.markdown("### ℹ️ System Info")
        st.info("""
        **Version:** 3.0.0
        **Environment:** Production
        **Database:** Connected
        """)
        
        # Help section
        st.markdown("---")
        st.markdown("### 📚 Quick Help")
        with st.expander("Getting Started"):
            st.markdown("""
            1. **Configure API Keys**: Enter your Samsara and Fleetrock API keys
            2. **View Dashboard**: Monitor real-time fleet status
            3. **Manage Repairs**: Track and manage repair orders
            4. **Generate Reports**: Create custom reports and analytics
            """)
        
        with st.expander("API Configuration"):
            st.markdown("""
            **Samsara API:**
            - Get your API token from Samsara portal
            - Token should start with 'samsara_'
            
            **Fleetrock API:**
            - Enable JWT in Fleetrock settings
            - Use your API key from account settings
            """)
        
        # Footer
        st.markdown("---")
        st.caption("""
        © 2024 Fleet Management System
        
        [Documentation](https://docs.example.com) | [Support](mailto:support@example.com)
        """)
    
    # Load the selected page
    if page == "Dashboard":
        # Import and run dashboard
        try:
            import dashboard
            dashboard.main()
        except ImportError as e:
            st.error(f"Failed to load Dashboard module: {str(e)}")
            st.info("Make sure dashboard.py is in the same directory as Dashboard.py")
        except Exception as e:
            st.error(f"Error in Dashboard: {str(e)}")
    
    elif page == "Repair Orders":
        # Import and run repair orders
        try:
            import repair_orders
            repair_orders.main()
        except ImportError as e:
            st.error(f"Failed to load Repair Orders module: {str(e)}")
            st.info("Make sure repair_orders.py is in the same directory as Dashboard.py")
        except Exception as e:
            st.error(f"Error in Repair Orders: {str(e)}")

if __name__ == "__main__":
    main()