from __future__ import annotations

import httpx
import pandas as pd
import streamlit as st

from shared.config import Settings


def _client() -> httpx.Client:
    settings = Settings()
    return httpx.Client(base_url=settings.api_base_url, timeout=120.0)


def _render_result(client: httpx.Client, result: dict) -> None:
    sql = result["generated_sql"]["sql"]

    st.subheader("Generated SQL")
    edited_sql = st.text_area("SQL (editable)", value=sql, height=120, key="sql_editor")
    st.code(sql, language="sql")

    if edited_sql.strip() != sql.strip():
        if st.button("Run edited SQL"):
            try:
                run = client.post("/v1/execute", json={"sql": edited_sql}).json()
            except httpx.HTTPStatusError as exc:
                st.error(exc.response.text)
            else:
                exec_ = run["execution"]
                df = pd.DataFrame(exec_["data"], columns=exec_["columns"])
                st.dataframe(df)
                if not run["guardrail"]["passed"]:
                    for v in run["guardrail"]["violations"]:
                        st.error(f"[{v['rule']}] {v['reason']}")
                st.caption("Confidence unchanged (still from the generated SQL).")

    conf = result["confidence_report"]
    st.metric("Confidence", f"{conf['overall']:.1f} / 100")

    signal_df = pd.DataFrame([
        {"signal": s["name"], "score": s["score"], "weight": s["weight"], "detail": s["detail"]}
        for s in conf["signals"]
    ])
    st.dataframe(signal_df)
    st.bar_chart(signal_df.set_index("signal")[["score"]])

    for f in conf.get("flags", []):
        st.warning(f)
    if not result["guardrail"]["passed"]:
        for v in result["guardrail"]["violations"]:
            st.error(f"[{v['rule']}] {v['reason']}")

    exec_ = result["execution"]
    st.subheader("Results")
    st.dataframe(pd.DataFrame(exec_["data"], columns=exec_["columns"]))
    st.caption(
        f"{exec_['row_count']} rows · {exec_['execution_time_ms']:.2f} ms"
        + (" · truncated" if exec_["truncated"] else "")
    )

    c1, c2 = st.columns(2)
    with c1:
        if st.button("Correct", key="correct"):
            client.post("/v1/feedback", json={"query_id": result["query_id"], "rating": "correct"})
            st.success("Marked correct — added to few-shot examples.")
    with c2:
        if st.button("Incorrect", key="incorrect"):
            client.post("/v1/feedback", json={"query_id": result["query_id"], "rating": "incorrect"})
            st.warning("Marked incorrect — added as an eval regression case.")


def main() -> None:
    st.set_page_config(page_title="Text-to-SQL", layout="wide")
    st.title("Text-to-SQL")

    client = _client()

    with st.sidebar:
        st.header("Session")
        session_id = st.text_input("Session ID", value="default")
        st.header("History")
        try:
            history = client.get("/v1/history", params={"session_id": session_id}).json()
        except Exception:
            history = []
        for item in history:
            label = f"{item['confidence']} · {item['question'][:40]}"
            if st.button(label, key=item["query_id"]):
                st.session_state["selected_query_id"] = item["query_id"]

    question = st.text_input(
        "Ask a question about the database",
        placeholder="e.g. which store generated the most revenue",
    )

    if st.button("Run", type="primary") and question.strip():
        try:
            result = client.post(
                "/v1/query", json={"question": question.strip(), "session_id": session_id}
            ).json()
        except httpx.HTTPStatusError as exc:
            st.error(exc.response.text)
        except Exception as exc:
            st.error(str(exc))
        else:
            st.session_state["result"] = result
            _render_result(client, result)

    selected = st.session_state.get("selected_query_id")
    if selected and st.button("Load selected query"):
        try:
            result = client.get(f"/v1/query/{selected}").json()
        except Exception as exc:
            st.error(str(exc))
        else:
            st.session_state["result"] = result
            _render_result(client, result)


if __name__ == "__main__":
    main()
