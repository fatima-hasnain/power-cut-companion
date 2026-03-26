import streamlit as st

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


def suggest_fix(counts, total_watts, avail_wh, cut_min):

    needed_max_watts = (avail_wh / cut_min) * 60

    all_options = []
    for name, qty in counts.items():
        for remove in range(1, qty + 1):
            saved = APPLIANCES[name] * remove
            new_watts = total_watts - saved
            if new_watts <= 0:
                continue
            new_runtime = round((avail_wh / new_watts) * 60)
            all_options.append({
                "name": name,
                "remove": remove,
                "saved": saved,
                "new_watts": new_watts,
                "new_runtime": new_runtime,
                "label": f"{remove}x {name}" if remove > 1 else name
            })

    all_options.sort(key=lambda x: x["saved"])

    single_fixes = [o for o in all_options if o["new_watts"] <= needed_max_watts]

    if single_fixes:
        st.write("Minimum you need to turn off to make it through:")
        seen_names = set()
        shown = 0
        for o in single_fixes:
            if o["name"] not in seen_names:
                seen_names.add(o["name"])
                spare = round(o["new_runtime"] - cut_min)
                st.success(
                    f"Turn off {o['label']} (saves {o['saved']}W) — "
                    f"runtime becomes {o['new_runtime']} min with {spare} min to spare."
                )
                shown += 1
            if shown == 3:
                break
        return

    pair_fixes = []
    seen_labels = set()
    for i in range(len(all_options)):
        for j in range(i + 1, len(all_options)):
            o1 = all_options[i]
            o2 = all_options[j]

            if o1["name"] == o2["name"]:
                total_remove = o1["remove"] + o2["remove"]
                if total_remove > counts[o1["name"]]:
                    continue
                combined_saved = APPLIANCES[o1["name"]] * total_remove
                new_watts = total_watts - combined_saved
                label = f"{total_remove}x {o1['name']}"
            else:
                combined_saved = o1["saved"] + o2["saved"]
                new_watts = total_watts - combined_saved
                label = f"{o1['label']} + {o2['label']}"

            if new_watts <= 0 or label in seen_labels:
                continue

            if new_watts <= needed_max_watts:
                new_runtime = round((avail_wh / new_watts) * 60)
                spare = round(new_runtime - cut_min)
                pair_fixes.append({
                    "label": label,
                    "saved": combined_saved,
                    "new_runtime": new_runtime,
                    "spare": spare
                })
                seen_labels.add(label)

    if pair_fixes:
        pair_fixes.sort(key=lambda x: x["saved"])
        st.write("Turn off these to make it through:")
        for p in pair_fixes[:3]:
            st.success(
                f"Turn off {p['label']} (saves {p['saved']}W) — "
                f"runtime {p['new_runtime']} min with {p['spare']} min to spare."
            )
        return

    sorted_names = sorted(counts.keys(), key=lambda x: APPLIANCES[x])
    keep = {}
    keep_watts = 0

    for name in sorted_names:
        for q in range(counts[name], 0, -1):
            test_watts = keep_watts + APPLIANCES[name] * q
            if test_watts <= needed_max_watts:
                keep[name] = q
                keep_watts = test_watts
                break

    turn_off_parts = []
    for name in counts:
        if name not in keep:
            turn_off_parts.append(f"all {name}")
        elif keep[name] < counts[name]:
            diff = counts[name] - keep[name]
            turn_off_parts.append(f"{diff}x {name}")

    if keep_watts > 0:
        survival_runtime = round((avail_wh / keep_watts) * 60)
        keep_labels = [f"{q}x {n}" if q > 1 else n for n, q in keep.items()]
        st.write("Switch to survival mode — reduce to these:")
        st.success(
            f"Keep: {', '.join(keep_labels)} — "
            f"total {round(keep_watts)}W — runtime {survival_runtime} min."
        )
        if turn_off_parts:
            st.error(f"Turn off: {', '.join(turn_off_parts)}")
    else:
        st.error("Load is too heavy for this UPS no matter what. Consider upgrading.")


st.set_page_config(page_title="Load Shed Buddy", page_icon="⚡", layout="wide")

st.title("Load Shed Buddy")
st.caption("Find out if your UPS will last the cut — and exactly what to turn off if it won't.")

st.divider()

st.subheader("Step 1 — UPS Configuration")

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

st.divider()

st.subheader("Step 2 — Add Your Appliances")

counts = {}
with st.expander("Select appliances and quantities"):
    cols = st.columns(2)
    for i, (name, watts) in enumerate(APPLIANCES.items()):
        with cols[i % 2]:
            qty = st.number_input(
                f"{name} ({watts}W)",
                min_value=0,
                max_value=20,
                value=0,
                step=1,
                key=name
            )
            if qty > 0:
                counts[name] = qty

st.divider()

w_cap = ups_va * 0.8
eff = BAT_EFFICIENCY[bat_age]
avail_wh = w_cap * eff * 0.9
total_watts = sum(APPLIANCES[name] * qty for name, qty in counts.items())
cut_min = cut_hours * 60
runtime_min = round((avail_wh / total_watts) * 60) if total_watts > 0 else 0

st.subheader("Step 3 — Results")

col1, col2, col3 = st.columns(3)
col1.metric("Active load", f"{total_watts} W")
col2.metric("Available energy", f"{round(avail_wh)} Wh")
col3.metric("Estimated runtime", f"{runtime_min} min" if total_watts > 0 else "-- min")

if total_watts > 0:
    load_pct = min(total_watts / w_cap, 1.0)
    st.progress(load_pct, text=f"Load is at {round(load_pct * 100)}% of UPS capacity")

st.divider()

st.subheader("Step 4 — Survival Plan")

if not counts:
    st.info("Add appliances above to get your survival plan.")
elif total_watts > w_cap * 0.9:
    st.error("Overload warning — your load is too close to UPS capacity. Turn off heavy appliances.")
elif runtime_min >= cut_min:
    spare = round(runtime_min - cut_min)
    st.success(f"You will last the full cut with {spare} minutes to spare.")
else:
    deficit = round(cut_min - runtime_min)
    st.error(f"Your UPS will run out {deficit} minutes before the cut ends.")
    suggest_fix(counts, total_watts, avail_wh, cut_min)
