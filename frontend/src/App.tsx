import React, { useState } from "react";
import { Tabs } from "antd";
import {
  DatabaseOutlined, ApartmentOutlined, FileSearchOutlined,
  SafetyCertificateOutlined, VideoCameraOutlined,
} from "@ant-design/icons";
import DatasetManager from "./pages/DatasetManager";
import Workbench from "./pages/Workbench";
import QaManager from "./pages/QaManager";
import VerifyPanel from "./pages/VerifyPanel";
import Scenario5Panel from "./pages/Scenario5Panel";

type View = "datasets" | "workbench" | "qa" | "check" | "scenario5";

export default function App() {
  const [view, setView] = useState<View>("datasets");
  const [pendingQuestion, setPendingQuestion] = useState<string | null>(null);
  const [workbenchDoc, setWorkbenchDoc] = useState<string | null>(null);

  const openInWorkbench = (q: string) => {
    setPendingQuestion(q);
    setView("workbench");
  };

  return (
    <div style={{ height: "100%", display: "flex", flexDirection: "column" }}>
      <header
        style={{
          height: 52, display: "flex", alignItems: "center", padding: "0 20px",
          background: "#fff", borderBottom: "1px solid #e5eaf1", flexShrink: 0,
        }}
      >
        <span style={{ fontSize: 15, fontWeight: 800, color: "#0f172a", letterSpacing: 0.5 }}>
          SRS 上下文关联图谱平台
        </span>
        <span style={{ fontSize: 11, color: "#94a3b8", marginLeft: 10, marginTop: 3 }}>
          GJB 438C · 数据集一致性校验 · 多模态动态召回
        </span>
        <Tabs
          activeKey={view}
          onChange={(k) => setView(k as View)}
          style={{ marginLeft: 28 }}
          items={[
            { key: "datasets", label: <span><DatabaseOutlined /> 数据集校验</span> },
            { key: "workbench", label: <span><ApartmentOutlined /> 图谱工作台</span> },
            { key: "qa", label: <span><FileSearchOutlined /> QA数据管理</span> },
            { key: "check", label: <span><SafetyCertificateOutlined /> 一致性校验</span> },
            { key: "scenario5", label: <span><VideoCameraOutlined /> 场景5安全帽</span> },
          ]}
        />
      </header>
      <main style={{ flex: 1, minHeight: 0 }}>
        {view === "datasets" && (
          <DatasetManager
            onOpenWorkbench={(docNum) => {
              setWorkbenchDoc(docNum);
              setView("workbench");
            }}
            onOpenCheck={() => setView("check")}
          />
        )}
        {view === "check" && <VerifyPanel />}
        {view === "scenario5" && <Scenario5Panel />}
        {view === "workbench" && (
          <Workbench
            pendingQuestion={pendingQuestion}
            onPendingConsumed={() => setPendingQuestion(null)}
            initialDoc={workbenchDoc}
          />
        )}
        {view === "qa" && <QaManager onOpenInWorkbench={openInWorkbench} />}
      </main>
    </div>
  );
}
