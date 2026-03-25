import streamlit as st

st.title("Power Cut Companion")
st.write("Figure out what you can run during a load shedding cut.")

APPLIANCES = {
    "Ceiling fan": 75,
    "Pedestal fan": 55,
    "LED bulb": 10,
    "Tube light": 36,
    "CFL bulb": 23,
    "WiFi router": 10,
    "Phone charger": 15,
    "Laptop charger": 65,
    "Small TV (32\")": 50,
    "Large TV (55\")": 150,
    "Mini fridge": 100,
    "Desktop PC": 200,
    "Air cooler": 180,
}

BAT_EFFICIENCY = {
    "Less than 1 year (100%)": 1.0,
    "1 to 2 years (80%)": 0.8,
    "2 to 3 years (60%)": 0.6,
    "3 or more years (40%)": 0.4,
}

st.header("Step 1 — UPS Configurations")

col1, col2 = st.columns(2)

with col1:
    ups_va = st.selectbox(
        "UPS capacity",
        [600, 1000, 1500, 2000],
        index=1,
        format_func=lambda x: f"{x} VA"
    )

with col2:
    bat_age = st.selectbox(
        "Battery age",
        list(BAT_EFFICIENCY.keys()),
        index=1
    )

cut_hours = st.number_input(
    "Expected cut duration (hours)",
    min_value=0.5,
    max_value=12.0,
    value=2.0,
    step=0.5
)

st.header("Step 2 — Add Your Appliances")

counts = {}
with st.expander("Adjust quantities for your appliances"):
    cols = st.columns(2)
    for i, (name, watts) in enumerate(APPLIANCES.items()):
        with cols[i % 2]:
            qty = st.number_input(f"{name} ({watts}W)", min_value=0, max_value=20, value=0, step=1, key=name)
            if qty > 0:
                counts[name] = qty

st.header("Step 3 — Results")

w_cap = ups_va * 0.8
eff = BAT_EFFICIENCY[bat_age]
avail_wh = w_cap * eff * 0.9
total_watts = sum(APPLIANCES[name] * qty for name, qty in counts.items())
cut_min = cut_hours * 60
runtime_min = round((avail_wh / total_watts) * 60) if total_watts > 0 else 0

col1, col2, col3 = st.columns(3)

col1.metric("Active load", f"{total_watts} W")
col2.metric("Available energy", f"{round(avail_wh)} Wh")
col3.metric("Estimated runtime", f"{runtime_min} min" if total_watts > 0 else "-- min")

if total_watts > 0:
    load_pct = min(total_watts / w_cap, 1.0)
    st.write("Load vs UPS capacity:")
    st.progress(load_pct)

st.header("Step 4 — Survival Plan")

if not counts:
    st.info("Select some appliances above to get your survival plan.")

elif total_watts > w_cap * 0.9:
    st.error("Overload warning — your load is too close to UPS capacity. Turn off heavy appliances.")

elif runtime_min >= cut_min:
    spare = round(runtime_min - cut_min)
    st.success(f"You are covered for the full cut with {spare} minutes to spare.")

else:
    deficit = round(cut_min - runtime_min)
    st.error(f"Your UPS will run out {deficit} minutes before the cut ends.")

    sorted_active = sorted(counts.keys(), key=lambda x: APPLIANCES[x], reverse=True)
    fixed = False
    for name in sorted_active:
        new_watts = total_watts - APPLIANCES[name]
        if new_watts <= 0:
            continue
        new_runtime = round((avail_wh / new_watts) * 60)
        if new_runtime >= cut_min:
            st.warning(f"Quick fix: turn off one {name} and your runtime becomes {new_runtime} minutes — enough for the full cut.")
            fixed = True
            break

    if not fixed:
        st.warning("You need to turn off multiple devices. Keep only fans and phone chargers on.")
