# -*- coding: utf-8 -*-
"""评分排行榜：人员榜 / 班组楼层榜 / 整改榜，多周期切换，权限内可见，可导出"""
from datetime import datetime

import pandas as pd
import streamlit as st
from sqlalchemy.orm import Session

from auth import current_user, visible_user_ids
from services.scoring import leaderboard
from views.common import kpi_card


def render(session: Session):
    user = current_user(session)
    st.header("评分排行榜")
    st.caption("多维度排行：人员榜（隐患发现量/整改及时率/巡检完成率）· 班组楼层榜（区域综合得分/闭环率）· 整改榜（整改速度/复查通过率）")

    c1, c2 = st.columns(2)
    period = c1.selectbox("时间维度", ["日", "周", "月", "季", "年"], key="lb_period")
    scope = c2.radio("可见范围（按权限）", ["权限内"], key="lb_scope")

    # 行级过滤
    vis_ids = visible_user_ids(session, user)
    data = leaderboard(session, period=period, scope_user_ids=vis_ids,
                       role_level=user.role_level, user_id=user.id)
    now = datetime.now()
    period_label = {"日": now.strftime("%m-%d"), "周": f"本周", "月": now.strftime("%Y-%m"),
                    "季": f"{now.year}Q{(now.month-1)//3+1}", "年": str(now.year)}[period]

    # 权限裁剪：一级全机构；二级仅本部门；三级仅个人排名 + 同组基准分
    show_people = data["people"]
    if user.role_level == 3:
        me = [p for p in show_people if p["user_id"] == user.id]
        base = show_people[0] if show_people else {}
        st.info(f"您的排名：{'第 ' + str(next((i+1 for i, p in enumerate(data['people']) if p['user_id'] == user.id), '—')) + ' 名'}"
                f"　·　综合得分 {me[0]['综合得分'] if me else '—'}"
                f"　·　同组基准分 {base.get('综合得分', '—') if base else '—'}")
        show_people = me

    tab1, tab2, tab3 = st.tabs(["👤 人员榜", "🏢 班组/楼层榜", "🔧 整改榜"])
    with tab1:
        st.caption(f"期间：{period_label}")
        if show_people:
            df = pd.DataFrame(show_people)
            st.dataframe(df.drop(columns=["user_id"], errors="ignore"), use_container_width=True, hide_index=True)
            csv = df.drop(columns=["user_id"], errors="ignore").to_csv(index=False).encode("utf-8-sig")
            st.download_button("⬇️ 导出人员榜 CSV", csv, f"人员榜_{period_label}.csv", "text/csv")
        else:
            st.caption("无数据")
    with tab2:
        if user.role_level == 3:
            st.info("三级账号仅可查看个人排名（见人员榜）")
        elif data["teams"]:
            st.dataframe(pd.DataFrame(data["teams"]), use_container_width=True, hide_index=True)
        else:
            st.caption("该周期暂无班组数据")
    with tab3:
        if user.role_level == 3:
            st.info("三级账号仅可查看个人排名（见人员榜）")
        else:
            df = pd.DataFrame(data["rectify"])
            if df.empty:
                st.caption("该周期无整改数据")
            else:
                st.dataframe(df.drop(columns=["user_id"], errors="ignore"), use_container_width=True, hide_index=True)

    # 绩效联动提示
    st.caption("排行数据可直接导出 CSV，对接人员评优与绩效核算。")
