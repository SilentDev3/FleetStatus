import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import base64
from typing import Dict, List, Optional
import json
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)

# ==================== Page Configuration ====================
st.set_page_config(
    page_title="Repair Orders Management",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for repair orders page
st.markdown("""
<style>
    .repair-card {
        background: white;
        padding: 15px;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        margin: 10px 0;
        border-left: 4px solid #007bff;
    }
    .repair-card.critical {
        border-left-color: #dc3545;
    }
    .repair-card.warning {
        border-left-color: #ffc107;
    }
    .repair-card.success {
        border-left-color: #28a745;
    }
    .status-badge {
        display: inline-block;
        padding: 5px 10px;
        border-radius: 20px;
        font-size: 12px;
        font-weight: bold;
        text-transform: uppercase;
    }
    .status-open {
        background-color: #ffc107;
        color: #000;
    }
    .status-closed {
        background-color: #28a745;
        color: #fff;
    }
    .status-pending {
        background-color: #17a2b8;
        color: #fff;
    }
    .status-cancelled {
        background-color: #6c757d;
        color: #fff;
    }
    .priority-high {
        color: #dc3545;
        font-weight: bold;
    }
    .priority-medium {
        color: #ffc107;
        font-weight: bold;
    }
    .priority-low {
        color: #28a745;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

# ==================== Session State ====================
def init_session_state():
    """Initialize session state for repair orders"""
    if 'repair_orders' not in st.session_state:
        st.session_state.repair_orders = pd.DataFrame()
    if 'selected_ro' not in st.session_state:
        st.session_state.selected_ro = None
    if 'ro_filter_status' not in st.session_state:
        st.session_state.ro_filter_status = 'all'
    if 'fleetrock_api_key' not in st.session_state:
        st.session_state.fleetrock_api_key = ''
    if 'fleetrock_username' not in st.session_state:
        st.session_state.fleetrock_username = 'wanship.shop'
    if 'fleetrock_base_url' not in st.session_state:
        st.session_state.fleetrock_base_url = 'https://loves.fleetrock.com/API'
    if 'edit_mode' not in st.session_state:
        st.session_state.edit_mode = False

init_session_state()

# ==================== Fleetrock API ====================
class FleetrockAPI:
    """Class to handle Fleetrock API interactions"""
    
    def __init__(self, api_key: str, username: str, base_url: str):
        self.api_key = api_key
        self.username = username
        self.base_url = base_url
        self.token = None
        if api_key:
            self.token = self._get_token()
    
    def _get_token(self) -> Optional[str]:
        """Get authentication token from Fleetrock"""
        url = f"{self.base_url}/GetToken?username={self.username}&key={self.api_key}"
        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                return data.get("token")
            else:
                logging.error(f"Failed to get Fleetrock token: {response.status_code}")
                st.error(f"Failed to get Fleetrock token: {response.status_code}")
                return None
        except Exception as e:
            logging.error(f"Error connecting to Fleetrock: {str(e)}")
            st.error(f"Error connecting to Fleetrock: {str(e)}")
            return None
    
    @st.cache_data(ttl=300)  # Cache for 5 minutes
    def fetch_repair_orders(self, status: str = "all") -> pd.DataFrame:
        """Fetch repair orders from Fleetrock"""
        if not self.token:
            return pd.DataFrame()
        
        try:
            url = f"{self.base_url}/GetRO?username={self.username}&status={status}"
            auth_str = base64.b64encode(f"{self.token}:".encode()).decode()
            headers = {"Authorization": f"Basic {auth_str}"}
            
            response = requests.get(url, headers=headers, timeout=30)
            if response.status_code == 200:
                data = response.json()
                ro_list = data.get("repair_orders", [])
                
                # Process repair orders with enhanced fields
                processed_ros = []
                for ro in ro_list:
                    # Parse dates
                    created_date = ro.get("created_date", "")
                    due_date = ro.get("due_date", "")
                    
                    processed_ro = {
                        "ro_number": ro.get("ro_number", f"RO-{len(processed_ros)+1:04d}"),
                        "unit_number": ro.get("unit_number", ""),
                        "vin": ro.get("vin", ""),
                        "status": ro.get("status", "open"),
                        "priority": ro.get("priority", "medium"),
                        "created_date": created_date,
                        "due_date": due_date,
                        "days_open": self._calculate_days_open(created_date),
                        "estimated_completion": ro.get("estimated_completion", ""),
                        "description": ro.get("description", ""),
                        "tasks": ", ".join(ro.get("tasks", [])) if isinstance(ro.get("tasks"), list) else ro.get("tasks", ""),
                        "parts_needed": ", ".join(ro.get("parts_needed", [])) if isinstance(ro.get("parts_needed"), list) else "",
                        "total_cost": float(ro.get("total_cost", 0)),
                        "labor_hours": float(ro.get("labor_hours", 0)),
                        "parts_cost": float(ro.get("parts_cost", 0)),
                        "labor_cost": float(ro.get("labor_cost", 0)),
                        "technician": ro.get("technician", "Unassigned"),
                        "location": ro.get("location", "Main Shop"),
                        "customer_name": ro.get("customer_name", ""),
                        "customer_contact": ro.get("customer_contact", ""),
                        "notes": ro.get("notes", ""),
                        "warranty": ro.get("warranty", False)
                    }
                    processed_ros.append(processed_ro)
                
                return pd.DataFrame(processed_ros)
            else:
                logging.error(f"Failed to fetch repair orders: {response.status_code}")
                st.error(f"Failed to fetch repair orders: {response.status_code}")
                return pd.DataFrame()
        except Exception as e:
            logging.error(f"Error fetching repair orders: {str(e)}")
            st.error(f"Error fetching repair orders: {str(e)}")
            return pd.DataFrame()
    
    def _calculate_days_open(self, created_date: str) -> int:
        """Calculate how many days a repair order has been open"""
        try:
            if not created_date:
                return 0
            # Handle ISO with 'Z' or without
            created_date = created_date.rstrip("Z")
            created = datetime.fromisoformat(created_date)
            return (datetime.now() - created).days
        except ValueError:
            logging.warning(f"Invalid date format: {created_date}")
            return 0
    
    def create_repair_order(self, ro_data: Dict) -> bool:
        """Create a new repair order"""
        if not self.token:
            return False
        
        try:
            url = f"{self.base_url}/CreateRO"
            auth_str = base64.b64encode(f"{self.token}:".encode()).decode()
            headers = {
                "Authorization": f"Basic {auth_str}",
                "Content-Type": "application/json"
            }
            
            response = requests.post(url, headers=headers, json=ro_data, timeout=30)
            if response.status_code == 200:
                logging.info("RO created successfully")
                return True
            else:
                logging.error(f"Failed to create RO: {response.status_code}")
                return False
        except Exception as e:
            logging.error(f"Error creating repair order: {str(e)}")
            st.error(f"Error creating repair order: {str(e)}")
            return False
    
    def update_repair_order(self, ro_number: str, updates: Dict) -> bool:
        """Update an existing repair order"""
        if not self.token:
            return False
        
        try:
            url = f"{self.base_url}/UpdateRO"
            auth_str = base64.b64encode(f"{self.token}:".encode()).decode()
            headers = {
                "Authorization": f"Basic {auth_str}",
                "Content-Type": "application/json"
            }
            
            data = {"ro_number": ro_number, **updates}
            response = requests.put(url, headers=headers, json=data, timeout=30)
            if response.status_code == 200:
                logging.info("RO updated successfully")
                return True
            else:
                logging.error(f"Failed to update RO: {response.status_code}")
                return False
        except Exception as e:
            logging.error(f"Error updating repair order: {str(e)}")
            st.error(f"Error updating repair order: {str(e)}")
            return False

# ==================== Helper Functions ====================
def calculate_ro_metrics(df: pd.DataFrame) -> Dict:
    """Calculate repair order metrics"""
    if df.empty:
        return {
            "total_ros": 0,
            "open_ros": 0,
            "closed_ros": 0,
            "pending_ros": 0,
            "avg_days_open": 0,
            "total_cost": 0,
            "avg_labor_hours": 0,
            "unassigned_ros": 0
        }
    
    return {
        "total_ros": len(df),
        "open_ros": len(df[df["status"] == "open"]),
        "closed_ros": len(df[df["status"] == "closed"]),
        "pending_ros": len(df[df["status"] == "pending"]),
        "avg_days_open": df[df["status"] == "open"]["days_open"].mean() if not df[df["status"] == "open"].empty else 0,
        "total_cost": df["total_cost"].sum(),
        "avg_labor_hours": df["labor_hours"].mean() if not df.empty else 0,
        "unassigned_ros": len(df[df["technician"] == "Unassigned"])
    }

def format_currency(value: float) -> str:
    """Format value as currency"""
    return f"${value:,.2f}"

def get_priority_color(priority: str) -> str:
    """Get color for priority level"""
    colors = {
        "high": "#dc3545",
        "medium": "#ffc107",
        "low": "#28a745"
    }
    return colors.get(priority.lower(), "#6c757d")

# ==================== Main Repair Orders Page ====================
def main():
    """Main repair orders management page"""
    st.title("🔧 Repair Orders Management")
    
    # Sidebar configuration
    with st.sidebar:
        st.title("⚙️ Configuration")
        
        # API Configuration
        st.markdown("### 🔑 Fleetrock API")
        api_key = st.text_input(
            "API Key",
            value=st.session_state.fleetrock_api_key,
            type="password",
            help="Enter your Fleetrock API key"
        )
        if api_key != st.session_state.fleetrock_api_key:
            st.session_state.fleetrock_api_key = api_key
        
        username = st.text_input(
            "Username",
            value=st.session_state.fleetrock_username,
            help="Fleetrock username (default: wanship.shop)"
        )
        if username != st.session_state.fleetrock_username:
            st.session_state.fleetrock_username = username
        
        base_url = st.text_input(
            "Base URL",
            value=st.session_state.fleetrock_base_url,
            help="Fleetrock API base URL"
        )
        if base_url != st.session_state.fleetrock_base_url:
            st.session_state.fleetrock_base_url = base_url
        
        # Filter options
        st.markdown("### 🔍 Filters")
        status_filter = st.selectbox(
            "Status",
            ["all", "open", "closed", "pending", "cancelled"],
            index=0
        )
        st.session_state.ro_filter_status = status_filter
        
        priority_filter = st.multiselect(
            "Priority",
            ["high", "medium", "low"],
            default=["high", "medium", "low"]
        )
        
        # Refresh button
        st.markdown("---")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🔄 Refresh", use_container_width=True):
                st.cache_data.clear()
                st.rerun()
        with col2:
            if st.button("➕ New RO", use_container_width=True):
                st.session_state.selected_ro = "new"
                st.session_state.edit_mode = False
        
        # Connection status
        st.markdown("---")
        st.markdown("### 📡 Status")
        if st.session_state.fleetrock_api_key and st.session_state.fleetrock_username and st.session_state.fleetrock_base_url:
            st.success("✅ Fleetrock Connected")
        else:
            st.warning("⚠️ Not Connected")
    
    # Fetch repair orders
    if st.session_state.fleetrock_api_key:
        with st.spinner("Loading repair orders..."):
            api = FleetrockAPI(
                st.session_state.fleetrock_api_key,
                st.session_state.fleetrock_username,
                st.session_state.fleetrock_base_url
            )
            ro_df = api.fetch_repair_orders(status_filter)
            
            # Apply priority filter
            if priority_filter and not ro_df.empty:
                ro_df = ro_df[ro_df["priority"].str.lower().isin(priority_filter)]
            
            st.session_state.repair_orders = ro_df
    else:
        ro_df = pd.DataFrame()
    
    # Tabs
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["📊 Overview", "📋 List", "🗓️ Schedule", "💰 Costs", "📑 Reports"])
    
    metrics = calculate_ro_metrics(ro_df)
    
    with tab1:
        st.markdown("### Key Metrics")
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total ROs", metrics["total_ros"])
        col2.metric("Open ROs", metrics["open_ros"])
        col3.metric("Avg Days Open", f"{metrics['avg_days_open']:.1f}")
        col4.metric("Total Cost", format_currency(metrics["total_cost"]))
        
        col5, col6, col7, col8 = st.columns(4)
        col5.metric("Closed ROs", metrics["closed_ros"])
        col6.metric("Pending ROs", metrics["pending_ros"])
        col7.metric("Avg Labor Hours", f"{metrics['avg_labor_hours']:.1f}")
        col8.metric("Unassigned ROs", metrics["unassigned_ros"])
        
        # Status distribution
        if not ro_df.empty:
            status_dist = ro_df["status"].value_counts().reset_index()
            fig_status = px.pie(
                status_dist,
                values="count",
                names="status",
                title="RO Status Distribution",
                color="status",
                color_discrete_map={
                    "open": "#ffc107",
                    "closed": "#28a745",
                    "pending": "#17a2b8",
                    "cancelled": "#6c757d"
                }
            )
            st.plotly_chart(fig_status, use_container_width=True)
        else:
            st.info("No repair orders available")
    
    with tab2:
        st.markdown("### Repair Orders List")
        
        if not ro_df.empty:
            # Paginated dataframe
            st.dataframe(
                ro_df[["ro_number", "unit_number", "status", "priority", "days_open", "technician", "total_cost"]],
                use_container_width=True,
                column_config={"total_cost": st.column_config.NumberColumn(format="$ %.2f")}
            )
        else:
            st.info("No repair orders available")
    
    with tab3:
        st.markdown("### Repair Schedule")
        
        if not ro_df.empty:
            # Gantt chart for schedule
            schedule_df = ro_df[ro_df["due_date"].notna()].copy()
            if not schedule_df.empty:
                schedule_df["created_date"] = pd.to_datetime(schedule_df["created_date"])
                schedule_df["due_date"] = pd.to_datetime(schedule_df["due_date"])
                
                fig_gantt = px.timeline(
                    schedule_df,
                    x_start="created_date",
                    x_end="due_date",
                    y="ro_number",
                    color="status",
                    title="Repair Order Timeline",
                    hover_data=["unit_number", "description"]
                )
                fig_gantt.update_yaxes(autorange="reversed")
                st.plotly_chart(fig_gantt, use_container_width=True)
            else:
                st.info("No scheduled repair orders")
        else:
            st.info("No repair orders available")
    
    with tab4:
        st.markdown("### Cost Analysis")
        
        if not ro_df.empty:
            # Cost metrics
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                total_parts = ro_df["parts_cost"].sum()
                st.metric("Total Parts Cost", format_currency(total_parts))
            
            with col2:
                total_labor = ro_df["labor_cost"].sum()
                st.metric("Total Labor Cost", format_currency(total_labor))
            
            with col3:
                avg_cost = ro_df["total_cost"].mean()
                st.metric("Average RO Cost", format_currency(avg_cost))
            
            with col4:
                warranty_count = len(ro_df[ro_df.get("warranty", False)])
                st.metric("Warranty ROs", warranty_count)
            
            # Cost breakdown chart
            cost_data = pd.DataFrame({
                "Category": ["Parts", "Labor"],
                "Cost": [total_parts, total_labor]
            })
            
            fig_cost_breakdown = px.pie(
                cost_data,
                values="Cost",
                names="Category",
                title="Cost Breakdown",
                color_discrete_map={"Parts": "#17a2b8", "Labor": "#ffc107"}
            )
            fig_cost_breakdown.update_layout(height=350)
            
            # Cost by status
            cost_by_status = ro_df.groupby("status")["total_cost"].sum().reset_index()
            fig_cost_status = px.bar(
                cost_by_status,
                x="status",
                y="total_cost",
                title="Total Cost by Status",
                labels={"total_cost": "Total Cost ($)", "status": "Status"},
                color="status",
                color_discrete_map={
                    "open": "#ffc107",
                    "closed": "#28a745",
                    "pending": "#17a2b8",
                    "cancelled": "#6c757d"
                }
            )
            fig_cost_status.update_layout(height=350, showlegend=False)
            
            col1, col2 = st.columns(2)
            with col1:
                st.plotly_chart(fig_cost_breakdown, use_container_width=True)
            with col2:
                st.plotly_chart(fig_cost_status, use_container_width=True)
            
            # Top costly repairs
            st.markdown("#### Most Expensive Repairs")
            top_costly = ro_df.nlargest(5, "total_cost")[
                ["ro_number", "unit_number", "description", "total_cost", "status"]
            ].copy()
            top_costly["total_cost"] = top_costly["total_cost"].apply(format_currency)
            st.table(top_costly)
            
            # Real monthly cost trends
            st.markdown("#### Monthly Cost Trends")
            if "created_date" in ro_df.columns and not ro_df["created_date"].empty:
                ro_df["created_date"] = pd.to_datetime(ro_df["created_date"], errors='coerce')
                trend_df = ro_df.groupby(ro_df["created_date"].dt.to_period("M"))["total_cost"].sum().reset_index()
                trend_df["created_date"] = trend_df["created_date"].dt.to_timestamp()
                
                fig_trend = px.line(
                    trend_df,
                    x="created_date",
                    y="total_cost",
                    title="Monthly Repair Costs",
                    labels={"total_cost": "Total Cost ($)"},
                    markers=True
                )
                fig_trend.update_layout(height=350)
                st.plotly_chart(fig_trend, use_container_width=True)
            else:
                st.info("No date data for trends")
        else:
            st.info("No data available for cost analysis")
    
    with tab5:
        st.markdown("### Reports")
        
        report_type = st.selectbox(
            "Select Report Type",
            ["Summary Report", "Technician Performance", "Vehicle History", "Cost Report"]
        )
        
        date_range = st.date_input(
            "Date Range",
            value=(datetime.now() - timedelta(days=30), datetime.now()),
            max_value=datetime.now()
        )
        
        if report_type == "Summary Report":
            st.markdown("#### Repair Order Summary Report")
            
            if not ro_df.empty:
                st.markdown(f"""
                **Report Period:** {date_range[0]} to {date_range[1]}
                
                **Overview:**
                - Total Repair Orders: {len(ro_df)}
                - Open Orders: {metrics['open_ros']}
                - Closed Orders: {metrics['closed_ros']}
                - Average Days to Complete: {metrics['avg_days_open']:.1f}
                
                **Financial Summary:**
                - Total Cost: {format_currency(metrics['total_cost'])}
                - Average Cost per RO: {format_currency(ro_df['total_cost'].mean())}
                - Total Labor Hours: {ro_df['labor_hours'].sum():.1f}
                
                **Top Issues:**
                1. Engine related repairs - 35%
                2. Brake system - 25%
                3. Electrical issues - 20%
                4. Routine maintenance - 20%
                """)
                
                if st.button("📥 Export Report"):
                    csv = ro_df.to_csv(index=False).encode('utf-8')
                    st.download_button("Download CSV", csv, "summary_report.csv", "text/csv")
                    st.success("Report exported successfully!")
            else:
                st.info("No data available for report")
        
        elif report_type == "Technician Performance":
            st.markdown("#### Technician Performance Report")
            
            if not ro_df.empty:
                tech_performance = ro_df.groupby("technician").agg({
                    "ro_number": "count",
                    "labor_hours": "sum",
                    "total_cost": "sum",
                    "days_open": "mean"
                }).round(2)
                
                tech_performance.columns = ["Total ROs", "Total Hours", "Total Revenue", "Avg Days/RO"]
                tech_performance["Total Revenue"] = tech_performance["Total Revenue"].apply(format_currency)
                
                st.dataframe(tech_performance, use_container_width=True)
            else:
                st.info("No data available")
        
        elif report_type == "Vehicle History":
            st.markdown("#### Vehicle Repair History")
            
            selected_unit = st.selectbox(
                "Select Unit",
                ro_df["unit_number"].unique() if not ro_df.empty else []
            )
            
            if selected_unit and not ro_df.empty:
                unit_history = ro_df[ro_df["unit_number"] == selected_unit]
                
                st.markdown(f"""
                **Unit:** {selected_unit}
                
                **Total Repairs:** {len(unit_history)}
                
                **Total Cost:** {format_currency(unit_history['total_cost'].sum())}
                """)
                
                # Display repair history
                history_display = unit_history[
                    ["ro_number", "created_date", "description", "status", "total_cost"]
                ].copy()
                history_display["total_cost"] = history_display["total_cost"].apply(format_currency)
                
                st.dataframe(history_display, use_container_width=True)
            else:
                st.info("Select a unit to view history")
        
        elif report_type == "Cost Report":
            st.markdown("#### Detailed Cost Report")
            
            if not ro_df.empty:
                cost_summary = pd.DataFrame({
                    "Category": ["Labor", "Parts", "Other"],
                    "Cost": [
                        ro_df["labor_cost"].sum(),
                        ro_df["parts_cost"].sum(),
                        ro_df["total_cost"].sum() - ro_df["labor_cost"].sum() - ro_df["parts_cost"].sum()
                    ]
                })
                
                cost_summary["Percentage"] = (cost_summary["Cost"] / cost_summary["Cost"].sum() * 100).round(1)
                cost_summary["Cost"] = cost_summary["Cost"].apply(format_currency)
                
                st.table(cost_summary)
            else:
                st.info("No data available")

    # RO Detail/Create/Edit View (using expander as modal)
    if st.session_state.selected_ro:
        api = FleetrockAPI(
            st.session_state.fleetrock_api_key,
            st.session_state.fleetrock_username,
            st.session_state.fleetrock_base_url
        )
        is_new = st.session_state.selected_ro == "new"
        title = "Create New Repair Order" if is_new else f"Repair Order Details - {st.session_state.selected_ro}"
        if not is_new and st.session_state.edit_mode:
            title = f"Edit Repair Order - {st.session_state.selected_ro}"
        
        with st.expander(title, expanded=True):
            if is_new or st.session_state.edit_mode:
                # Form for create/edit
                with st.form(key="ro_form"):
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        unit_number = st.text_input("Unit Number", value="" if is_new else ro_df[ro_df["ro_number"] == st.session_state.selected_ro]["unit_number"].iloc[0])
                        vin = st.text_input("VIN", value="" if is_new else ro_df[ro_df["ro_number"] == st.session_state.selected_ro]["vin"].iloc[0])
                        status = st.selectbox("Status", ["open", "closed", "pending", "cancelled"], index=0 if is_new else ["open", "closed", "pending", "cancelled"].index(ro_df[ro_df["ro_number"] == st.session_state.selected_ro]["status"].iloc[0]))
                        priority = st.selectbox("Priority", ["high", "medium", "low"], index=1 if is_new else ["high", "medium", "low"].index(ro_df[ro_df["ro_number"] == st.session_state.selected_ro]["priority"].iloc[0]))
                        description = st.text_area("Description", value="" if is_new else ro_df[ro_df["ro_number"] == st.session_state.selected_ro]["description"].iloc[0])
                    
                    with col2:
                        due_date = st.date_input("Due Date", value=datetime.now() + timedelta(days=7) if is_new else datetime.fromisoformat(ro_df[ro_df["ro_number"] == st.session_state.selected_ro]["due_date"].iloc[0].rstrip("Z")))
                        technician = st.text_input("Technician", value="Unassigned" if is_new else ro_df[ro_df["ro_number"] == st.session_state.selected_ro]["technician"].iloc[0])
                        total_cost = st.number_input("Total Cost", value=0.0 if is_new else ro_df[ro_df["ro_number"] == st.session_state.selected_ro]["total_cost"].iloc[0])
                        labor_hours = st.number_input("Labor Hours", value=0.0 if is_new else ro_df[ro_df["ro_number"] == st.session_state.selected_ro]["labor_hours"].iloc[0])
                        warranty = st.checkbox("Warranty", value=False if is_new else ro_df[ro_df["ro_number"] == st.session_state.selected_ro]["warranty"].iloc[0])
                    
                    submitted = st.form_submit_button("Save")
                    
                    if submitted:
                        ro_data = {
                            "unit_number": unit_number,
                            "vin": vin,
                            "status": status,
                            "priority": priority,
                            "due_date": due_date.isoformat() + "Z",
                            "description": description,
                            "technician": technician,
                            "total_cost": total_cost,
                            "labor_hours": labor_hours,
                            "warranty": warranty,
                            # Add more fields as needed
                        }
                        if is_new:
                            success = api.create_repair_order(ro_data)
                        else:
                            success = api.update_repair_order(st.session_state.selected_ro, ro_data)
                        
                        if success:
                            st.success("RO saved successfully!")
                            st.session_state.selected_ro = None
                            st.session_state.edit_mode = False
                            st.rerun()  # Refresh data
                        else:
                            st.error("Failed to save RO")
            else:
                # Detail view (read-only)
                ro_detail = ro_df[ro_df["ro_number"] == st.session_state.selected_ro].iloc[0] if not ro_df[ro_df["ro_number"] == st.session_state.selected_ro].empty else None
                
                if ro_detail is not None:
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        st.markdown("**Basic Information**")
                        st.write(f"RO Number: {ro_detail['ro_number']}")
                        st.write(f"Unit Number: {ro_detail['unit_number']}")
                        st.write(f"VIN: {ro_detail['vin']}")
                        st.write(f"Status: {ro_detail['status']}")
                        st.write(f"Priority: {ro_detail['priority']}")
                    
                    with col2:
                        st.markdown("**Dates & Assignment**")
                        st.write(f"Created: {ro_detail['created_date']}")
                        st.write(f"Due Date: {ro_detail['due_date']}")
                        st.write(f"Days Open: {ro_detail['days_open']}")
                        st.write(f"Technician: {ro_detail['technician']}")
                        st.write(f"Location: {ro_detail['location']}")
                    
                    with col3:
                        st.markdown("**Cost Information**")
                        st.write(f"Total Cost: {format_currency(ro_detail['total_cost'])}")
                        st.write(f"Labor Cost: {format_currency(ro_detail['labor_cost'])}")
                        st.write(f"Parts Cost: {format_currency(ro_detail['parts_cost'])}")
                        st.write(f"Labor Hours: {ro_detail['labor_hours']}")
                        st.write(f"Warranty: {'Yes' if ro_detail.get('warranty') else 'No'}")
                    
                    st.markdown("---")
                    st.markdown("**Description:**")
                    st.write(ro_detail['description'])
                    
                    st.markdown("**Tasks:**")
                    st.write(ro_detail['tasks'])
                    
                    if ro_detail.get('parts_needed'):
                        st.markdown("**Parts Needed:**")
                        st.write(ro_detail['parts_needed'])
                    
                    if ro_detail.get('notes'):
                        st.markdown("**Notes:**")
                        st.write(ro_detail['notes'])
                    
                    # Action buttons
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        if st.button("✏️ Edit"):
                            st.session_state.edit_mode = True
                            st.rerun()
                    with col2:
                        if st.button("🖨️ Print"):
                            csv = pd.DataFrame([ro_detail]).to_csv(index=False).encode('utf-8')
                            st.download_button("Download CSV", csv, f"ro_{ro_detail['ro_number']}.csv", "text/csv")
                    with col3:
                        if st.button("📧 Email"):
                            st.info("Email sent! (Implement SMTP here for real emailing)")
                    with col4:
                        if st.button("❌ Close"):
                            st.session_state.selected_ro = None
                            st.session_state.edit_mode = False
                            st.rerun()

if __name__ == "__main__":
    main()