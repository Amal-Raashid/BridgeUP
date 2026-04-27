import streamlit as st
from datetime import datetime
from pathlib import Path

from bridgeup_langgraph.ui_runner import run_bridgeup
from agents.monitoring_agent import MonitoringAgent
from bridgeup_langgraph.graph import decision_node


# -----------------------------------------------------------
# CONFIG
# -----------------------------------------------------------
st.set_page_config(page_title="BridgeUp AI", layout="wide")
st.title("🚀 BridgeUp AI")
st.markdown("### ✨ Your personalized AI-powered learning journey is ready")


# -----------------------------------------------------------
# SIDEBAR
# -----------------------------------------------------------
goal = st.sidebar.text_input("🎯 Goal", "Backend Developer")
skills_input = st.sidebar.text_input("🧠 Known Skills", "Python")
weekly_hours = st.sidebar.number_input("⏳ Weekly Hours", 1, 80, 10)

run_btn = st.sidebar.button("🚀 Run BridgeUp")


# -----------------------------------------------------------
# HELPERS
# -----------------------------------------------------------
def parse_skills(text):
    return [s.strip() for s in text.split(",") if s.strip()]


def get_attr(obj, name, default=None):
    if hasattr(obj, name):
        return getattr(obj, name)
    if isinstance(obj, dict):
        return obj.get(name, default)
    return default


# -----------------------------------------------------------
# INIT SESSION
# -----------------------------------------------------------
def init_session(result):

    st.session_state.initialized = True

    st.session_state.session_id = result.get("session_id")
    st.session_state.strategy = result.get("selected_strategy")

    # 🔥 STORE EVERYTHING
    st.session_state.tasks = result.get("tasks", [])
    st.session_state.roadmap = result.get("roadmap")
    st.session_state.schedule_blocks = result.get("schedule_blocks", [])
    st.session_state.jobs = result.get("job_recommendations", [])
    st.session_state.execution_summary = result.get("execution_summary")

    st.session_state.metric = result.get("metric_snapshot")
    st.session_state.risk = result.get("risk_profile")

    st.session_state.decision = {
        "action": result.get("decision_action"),
        "reason": result.get("decision_reason")
    }

    st.session_state.adaptation_cycles = result.get("adaptation_cycles", 0)
    st.session_state.timeline = []

    st.session_state.monitor = MonitoringAgent(
        base_path=Path("data/monitoring_logs")
    )

    st.session_state.task_status = {
        t.task_id: "pending" for t in st.session_state.tasks
    }


# -----------------------------------------------------------
# CORE LOOP
# -----------------------------------------------------------
def update_task_status(task_id, event_type):

    monitor = st.session_state.monitor
    session_id = st.session_state.session_id
    strategy = st.session_state.strategy

    now = datetime.utcnow().isoformat()

    # 1. Record event
    monitor.collector.record_task_event({
        "event_type": event_type,
        "task_id": task_id,
        "session_id": session_id,
        "timestamp": now,
        "payload": {
            "strategy_type": strategy
        }
    })

    # 2. Local state
    if event_type == "TASK_COMPLETED":
        st.session_state.task_status[task_id] = "completed"
    elif event_type == "TASK_STARTED":
        st.session_state.task_status[task_id] = "in_progress"
    elif event_type == "TASK_MISSED":
        st.session_state.task_status[task_id] = "missed"

    # 3. Metrics
    monitor.collector.build_session_snapshot(
        session_id=session_id,
        weekly_hours_allocated=weekly_hours,
        planned_days=5
    )

    metric = monitor.get_session_metrics(session_id)
    st.session_state.metric = metric

    # 4. Decision
    state = {
        "selected_strategy": strategy,
        "metric_snapshot": metric,
        "adaptation_cycles": st.session_state.adaptation_cycles
    }

    decision = decision_node(state)

    st.session_state.decision = {
        "action": decision["decision_action"],
        "reason": decision["decision_reason"]
    }

    # 5. Timeline
    st.session_state.adaptation_cycles += 1
    st.session_state.timeline.append(
        f"Cycle {st.session_state.adaptation_cycles} → {decision['decision_action']}"
    )


# -----------------------------------------------------------
# RUN BACKEND
# -----------------------------------------------------------
if run_btn:
    skills = parse_skills(skills_input)
    result = run_bridgeup(goal, skills, weekly_hours)
    init_session(result)


# -----------------------------------------------------------
# STOP IF NOT READY
# -----------------------------------------------------------
if "initialized" not in st.session_state:
    st.info("Configure and run BridgeUp to start")
    st.stop()


# -----------------------------------------------------------
# TABS
# -----------------------------------------------------------
tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
    "🎯 Summary",
    "📘 Roadmap",
    "🗓️ Study Plan",
    "📊 Insights",
    "🧠 AI Decisions",
    "💼 Jobs",
    "🔁 Adaptation"
])


# ===========================================================
# 🎯 SUMMARY
# ===========================================================
with tab1:

    st.subheader("🎯 Your Learning Journey")

    st.markdown(f"**Goal:** {goal}")
    st.markdown(f"**Strategy:** {st.session_state.strategy}")

    metric = st.session_state.metric

    col1, col2, col3 = st.columns(3)
    col1.metric("Completion", f"{metric.completion_rate:.2f}")
    col2.metric("Dropoff", f"{metric.dropoff_risk_score:.2f}")
    col3.metric("Stability", f"{metric.stability_score:.2f}")


# ===========================================================
# 📘 ROADMAP
# ===========================================================
with tab2:

    roadmap = st.session_state.roadmap

    if roadmap and hasattr(roadmap, "steps"):
        for i, step in enumerate(roadmap.steps, 1):
            with st.container():
                st.markdown(f"### 🟢 Step {i}: {get_attr(step,'skill_name','Skill')}")

                for r in get_attr(step, "resources", [])[:3]:
                    st.markdown(f"- {get_attr(r,'title','Resource')}")

                st.divider()
    else:
        st.warning("No roadmap available")


# ===========================================================
# 🗓️ STUDY PLAN (INTERACTIVE)
# ===========================================================
with tab3:

    for task in st.session_state.tasks[:10]:

        task_id = task.task_id
        status = st.session_state.task_status.get(task_id)

        if status == "completed":
            st.success(f"✅ {task.title}")
        elif status == "missed":
            st.error(f"❌ {task.title}")
        elif status == "in_progress":
            st.warning(f"⏳ {task.title}")
        else:
            st.markdown(f"### 📘 {task.title}")

        col1, col2, col3 = st.columns(3)

        if col1.button("Complete", key=f"c_{task_id}"):
            update_task_status(task_id, "TASK_COMPLETED")

        if col2.button("Progress", key=f"p_{task_id}"):
            update_task_status(task_id, "TASK_STARTED")

        if col3.button("Missed", key=f"m_{task_id}"):
            update_task_status(task_id, "TASK_MISSED")

        st.divider()


# ===========================================================
# 📊 INSIGHTS
# ===========================================================
with tab4:

    metric = st.session_state.metric

    st.metric("Completion", f"{metric.completion_rate:.2f}")
    st.metric("Dropoff", f"{metric.dropoff_risk_score:.2f}")
    st.metric("Stability", f"{metric.stability_score:.2f}")

    if metric.dropoff_risk_score > 0.3:
        st.warning("⚠️ Burnout risk detected")
    else:
        st.success("Healthy learning pace")


# ===========================================================
# 🧠 AI DECISIONS
# ===========================================================
with tab5:

    decision = st.session_state.decision

    if decision["action"] == "adjust":
        st.warning("AI adjusted your plan due to performance")
    elif decision["action"] == "replan":
        st.error("AI is rebuilding your learning plan")
    else:
        st.success("Your plan is working well")

    st.markdown(f"**Reason:** {decision['reason']}")


# ===========================================================
# 💼 JOBS
# ===========================================================
with tab6:

    jobs = st.session_state.jobs

    if jobs:
        for job in jobs:
            st.markdown(f"### 💼 {get_attr(job,'title','Role')}")
            st.markdown(f"{get_attr(job,'company','Company')}")
            st.markdown("---")
    else:
        st.warning("No jobs available")


# ===========================================================
# 🔁 ADAPTATION
# ===========================================================
with tab7:

    for step in st.session_state.timeline:
        st.markdown(f"➡️ {step}")