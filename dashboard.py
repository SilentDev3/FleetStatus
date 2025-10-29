import streamlit as st
import requests
import pandas as pd
try:
    import plotly.express as px
    PLOTLY_AVAILABLE = True
except Exception:
    px = None
    PLOTLY_AVAILABLE = False
from datetime import datetime
import logging
from typing import Dict, List, Optional

# Setup logging
logging.basicConfig(level=logging.INFO)

# ==================== Page Configuration ====================
st.set_page_config(
    page_title="Fleet Dashboard",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for consistency with repair_orders
st.markdown("""
<style>
    .vehicle-card {
        background: white;
        padding: 15px;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        margin: 10px 0;
        border-left: 4px solid #007bff;
    }
    .status-moving { border-left-color: #28a745; }
    .status-idle { border-left-color: #ffc107; }
    .status-offline { border-left-color: #dc3545; }
    .alert-critical { color: #dc3545; font-weight: bold; }
    .alert-warning { color: #ffc107; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

# ==================== Session State ====================
def init_session_state():
    """Initialize session state for dashboard"""
    if 'vehicles_df' not in st.session_state:
        st.session_state.vehicles_df = pd.DataFrame()
    if 'locations_df' not in st.session_state:
        st.session_state.locations_df = pd.DataFrame()
    if 'stats_df' not in st.session_state:
        st.session_state.stats_df = pd.DataFrame()
    if 'drivers_df' not in st.session_state:
        st.session_state.drivers_df = pd.DataFrame()
    if 'selected_vehicle' not in st.session_state:
        st.session_state.selected_vehicle = None
    if 'vehicle_filter_status' not in st.session_state:
        st.session_state.vehicle_filter_status = 'all'

init_session_state()

# ==================== Samsara API ====================
class SamsaraAPI:
    """Class to handle Samsara API interactions"""
    
    def __init__(self, token: str):
        self.token = token
        self.base_url = "https://api.samsara.com"
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/json"
        }
    
    @st.cache_data(ttl=300)  # Cache for 5 minutes
    def fetch_vehicles(self) -> pd.DataFrame:
        """Fetch list of vehicles"""
        try:
            url = f"{self.base_url}/fleet/vehicles"
            response = requests.get(url, headers=self.headers, timeout=30)
            response.raise_for_status()
            data = response.json().get("data", [])
            processed_vehicles = []
            for v in data:
                processed_vehicles.append({
                    "id": v.get("id"),
                    "name": v.get("name"),
                    "vin": v.get("vin"),
                    "make": v.get("make"),
                    "model": v.get("model"),
                    "year": v.get("year"),
                    "license_plate": v.get("licensePlate"),
                    "serial": v.get("serial")
                })
            return pd.DataFrame(processed_vehicles)
        except Exception as e:
            logging.error(f"Error fetching vehicles: {str(e)}")
            st.error(f"Error fetching vehicles: {str(e)}")
            return pd.DataFrame()
    
    @st.cache_data(ttl=300)
    def fetch_vehicle_locations(self, vehicle_ids: List[str]) -> pd.DataFrame:
        """Fetch locations for vehicles"""
        try:
            locations = []
            for vid in vehicle_ids:
                url = f"{self.base_url}/fleet/vehicles/{vid}/location"
                response = requests.get(url, headers=self.headers, timeout=10)
                if response.status_code == 200:
                    loc = response.json()
                    locations.append({
                        "vehicle_id": vid,
                        "latitude": loc.get("latitude"),
                        "longitude": loc.get("longitude"),
                        "time": loc.get("time"),
                        "address": loc.get("formattedAddress")
                    })
            return pd.DataFrame(locations)
        except Exception as e:
            logging.error(f"Error fetching locations: {str(e)}")
            return pd.DataFrame()
    
    @st.cache_data(ttl=300)
    def fetch_vehicle_stats(self, vehicle_ids: List[str]) -> pd.DataFrame:
        """Fetch stats for vehicles (speed, fuel, engine hours)"""
        try:
            stats = []
            for vid in vehicle_ids:
                url = f"{self.base_url}/fleet/vehicles/{vid}/stats"
                response = requests.get(url, headers=self.headers, timeout=10)
                if response.status_code == 200:
                    s = response.json()
                    stats.append({
                        "vehicle_id": vid,
                        "speed_mph": s.get("speedMilesPerHour", 0),
                        "fuel_percent": s.get("fuelPercent", 0),
                        "engine_hours": s.get("engineHours", 0),
                        "odometer_miles": s.get("odometerMiles", 0),
                        "status": "moving" if s.get("speedMilesPerHour", 0) > 0 else "idle" if s.get("engineState") == "Running" else "offline"
                    })
            return pd.DataFrame(stats)
        except Exception as e:
            logging.error(f"Error fetching stats: {str(e)}")
            return pd.DataFrame()
    
    @st.cache_data(ttl=300)
    def fetch_drivers(self) -> pd.DataFrame:
        """Fetch list of drivers"""
        try:
            url = f"{self.base_url}/fleet/drivers"
            response = requests.get(url, headers=self.headers, timeout=30)
            response.raise_for_status()
            data = response.json().get("data", [])
            return pd.DataFrame([{"id": d["id"], "name": d["name"]} for d in data])
        except Exception as e:
            logging.error(f"Error fetching drivers: {str(e)}")
            return pd.DataFrame()
    
    @st.cache_data(ttl=300)
    def fetch_assignments(self) -> pd.DataFrame:
        """Fetch driver-vehicle assignments"""
        try:
            url = f"{self.base_url}/fleet/driver-vehicle-assignments"
            response = requests.get(url, headers=self.headers, timeout=30)
            response.raise_for_status()
            data = response.json().get("data", [])
            return pd.DataFrame([{"vehicle_id": a["vehicleId"], "driver_id": a["driverId"]} for a in data])
        except Exception as e:
            logging.error(f"Error fetching assignments: {str(e)}")
            return pd.DataFrame()

# ==================== Helper Functions ====================
def calculate_fleet_metrics(vehicles_df: pd.DataFrame, stats_df: pd.DataFrame) -> Dict:
    """Calculate fleet metrics"""
    if vehicles_df.empty or stats_df.empty:
        return {
            "total_vehicles": 0,
            "moving": 0,
            "idle": 0,
            "offline": 0,
            "avg_speed": 0,
            "total_engine_hours": 0,
            "low_fuel": 0
        }
    
    return {
        "total_vehicles": len(vehicles_df),
        "moving": len(stats_df[stats_df["status"] == "moving"]),
        "idle": len(stats_df[stats_df["status"] == "idle"]),
        "offline": len(stats_df[stats_df["status"] == "offline"]),
        "avg_speed": stats_df["speed_mph"].mean(),
        "total_engine_hours": stats_df["engine_hours"].sum(),
        "low_fuel": len(stats_df[stats_df["fuel_percent"] < 20])
    }

def generate_alerts(stats_df: pd.DataFrame) -> List[str]:
    """Generate alerts based on stats"""
    alerts = []
    for _, row in stats_df.iterrows():
        if row["speed_mph"] > 80:
            alerts.append(f"Vehicle {row['vehicle_id']}: Speeding ({row['speed_mph']} mph)")
        if row["fuel_percent"] < 20:
            alerts.append(f"Vehicle {row['vehicle_id']}: Low fuel ({row['fuel_percent']}%)")
    return alerts

# ==================== Main Dashboard Page ====================
def main():
    """Main fleet dashboard page"""
    st.title("🚛 Fleet Dashboard")
    
    # Sidebar (shared from Dashboard.py, but add local filters)
    with st.sidebar:
        st.markdown("### 🔍 Vehicle Filters")
        status_filter = st.selectbox(
            "Status",
            ["all", "moving", "idle", "offline"],
            index=0
        )
        st.session_state.vehicle_filter_status = status_filter
        
        if st.button("🔄 Refresh", use_container_width=True):
            st.cache_data.clear()
            st.rerun()
    
    # Fetch data if token available
    if st.session_state.samsara_token:
        with st.spinner("Loading fleet data..."):
            api = SamsaraAPI(st.session_state.samsara_token)
            vehicles_df = api.fetch_vehicles()
            if not vehicles_df.empty:
                vehicle_ids = vehicles_df["id"].tolist()
                locations_df = api.fetch_vehicle_locations(vehicle_ids)
                stats_df = api.fetch_vehicle_stats(vehicle_ids)
                drivers_df = api.fetch_drivers()
                assignments_df = api.fetch_assignments()
                
                # Merge data
                merged_df = vehicles_df.merge(stats_df, left_on="id", right_on="vehicle_id", how="left")
                merged_df = merged_df.merge(locations_df, left_on="id", right_on="vehicle_id", how="left")
                merged_df = merged_df.merge(assignments_df, on="vehicle_id", how="left")
                merged_df = merged_df.merge(drivers_df, left_on="driver_id", right_on="id", how="left", suffixes=("", "_driver"))
                
                st.session_state.vehicles_df = merged_df
            else:
                merged_df = pd.DataFrame()
    else:
        merged_df = pd.DataFrame()
        st.warning("Enter Samsara API token in the main sidebar to load data.")
    
    # Apply filter
    if st.session_state.vehicle_filter_status != "all" and not merged_df.empty:
        merged_df = merged_df[merged_df["status"] == st.session_state.vehicle_filter_status]
    
    # Tabs
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["📊 Overview", "🚗 Vehicles", "🗺️ Map", "📈 Analytics", "⚠️ Alerts"])
    
    metrics = calculate_fleet_metrics(merged_df, merged_df)  # Using merged_df for stats
    
    with tab1:
        st.markdown("### Key Metrics")
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total Vehicles", metrics["total_vehicles"])
        col2.metric("Moving", metrics["moving"])
        col3.metric("Idle", metrics["idle"])
        col4.metric("Offline", metrics["offline"])
        
        col5, col6, col7 = st.columns(3)
        col5.metric("Avg Speed (mph)", f"{metrics['avg_speed']:.1f}")
        col6.metric("Total Engine Hours", f"{metrics['total_engine_hours']:.1f}")
        col7.metric("Low Fuel Alerts", metrics["low_fuel"])
    
    with tab2:
        st.markdown("### Vehicle List")
        if not merged_df.empty:
            display_df = merged_df[["name", "vin", "status", "speed_mph", "fuel_percent", "engine_hours", "name_driver"]]
    with tab3:
        st.markdown("### Vehicle Locations Map")
        if px is None:
            st.warning("plotly is not available; install it with 'pip install plotly' to view maps and charts.")
        elif not merged_df.empty and "latitude" in merged_df.columns:
            fig_map = px.scatter_mapbox(
                merged_df,
                lat="latitude",
                lon="longitude",
                hover_name="name",
                hover_data=["status", "speed_mph", "fuel_percent"],
                color="status",
                color_discrete_map={"moving": "green", "idle": "orange", "offline": "red"},
                zoom=3,
                height=500
            )
            fig_map.update_layout(mapbox_style="open-street-map")
            st.plotly_chart(fig_map, use_container_width=True)
        else:
    with tab4:
        st.markdown("### Fleet Analytics")
        if px is None:
            st.warning("plotly is not available; install it with 'pip install plotly' to view analytics charts.")
        elif not merged_df.empty:
            col1, col2 = st.columns(2)
            with col1:
                fig_speed = px.histogram(merged_df, x="speed_mph", title="Speed Distribution")
                st.plotly_chart(fig_speed, use_container_width=True)
            with col2:
                fig_fuel = px.box(merged_df, y="fuel_percent", title="Fuel Levels")
                st.plotly_chart(fig_fuel, use_container_width=True)
            
            fig_engine = px.scatter(merged_df, x="engine_hours", y="odometer_miles", hover_name="name", title="Engine Hours vs Odometer")
            st.plotly_chart(fig_engine, use_container_width=True)
        else:
            st.info("No data for analytics")
                fig_fuel = px.box(merged_df, y="fuel_percent", title="Fuel Levels")
                st.plotly_chart(fig_fuel, use_container_width=True)
            
            fig_engine = px.scatter(merged_df, x="engine_hours", y="odometer_miles", hover_name="name", title="Engine Hours vs Odometer")
            st.plotly_chart(fig_engine, use_container_width=True)
        else:
            st.info("No data for analytics")
    
    with tab5:
        st.markdown("### Active Alerts")
        alerts = generate_alerts(merged_df)
        if alerts:
            for alert in alerts:
                st.markdown(f"- {alert}")
        else:
            st.info("No active alerts")

if __name__ == "__main__":
    main()