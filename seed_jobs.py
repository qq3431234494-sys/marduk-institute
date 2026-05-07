import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from db import get_db, create_user
import time

print("[1/3] Creating HR1 account...")
existing_id = None
conn = get_db()
cur = conn.cursor()

cur.execute("SELECT id FROM users WHERE username = ?", ("HR1",))
row = cur.fetchone()
if row:
    existing_id = row[0]
    print(f"  HR1 already exists (id={existing_id})")
else:
    uid, key = create_user("HR1", "123456", role="hr")
    existing_id = uid
    print(f"  HR1 created (id={uid})")

companies = {
    "北京": [
        ("字节跳动", "ByteDance"), ("百度", "Baidu"), ("京东", "JD.com"), ("美团", "Meituan"),
        ("快手", "Kuaishou"), ("小米", "Xiaomi"), ("滴滴", "DiDi"), ("网易北京", "NetEase BJ"),
        ("新浪", "Sina"), ("搜狐", "Sohu"), ("联想", "Lenovo"), ("360", "360"),
        ("商汤科技", "SenseTime"), ("旷视科技", "Megvii"), ("地平线", "Horizon"),
        ("寒武纪", "Cambricon"), ("贝壳找房", "Beike"), ("去哪儿", "Qunar"),
        ("知乎", "Zhihu"), ("米哈游北京", "miHoYo BJ")
    ],
    "上海": [
        ("拼多多", "Pinduoduo"), ("哔哩哔哩", "Bilibili"), ("携程", "Trip.com"), ("小红书", "RED"),
        ("米哈游", "miHoYo"), ("莉莉丝", "Lilith"), ("鹰角网络", "Hypergryph"), ("盛趣游戏", "Shengqu"),
        ("蚂蚁集团", "Ant Group"), ("喜马拉雅", "Ximalaya"), ("阅文集团", "China Literature"),
        ("陆金所", "Lu.com"), ("波克城市", "Boke"), ("七牛云", "Qiniu"), ("UCloud", "UCloud"),
        ("声网", "Agora"), ("依图科技", "Yitu"), ("流利说", "Liulishuo"),
        ("虎扑", "Hupu"), ("得物", "Poizon")
    ],
    "广州": [
        ("微信", "WeChat"), ("网易广州", "NetEase GZ"), ("欢聚时代", "YY"), ("唯品会", "Vipshop"),
        ("三七互娱", "37Games"), ("多益网络", "Duoyi"), ("4399", "4399"), ("酷狗", "Kugou"),
        ("荔枝FM", "Lizhi"), ("小鹏汽车", "XPeng"), ("极飞科技", "XAG"), ("汇量科技", "Mobvista"),
        ("佳都科技", "PCRTech"), ("金山软件广州", "Kingsoft GZ"), ("虎牙广州", "Huya GZ"),
        ("百果园", "Pagoda"), ("致景科技", "ZhiJing"), ("趣丸", "Quwan"),
        ("汇丰科技", "HSBC Tech"), ("中望软件", "ZWSOFT")
    ],
    "深圳": [
        ("腾讯", "Tencent"), ("华为", "Huawei"), ("大疆", "DJI"), ("中兴", "ZTE"),
        ("OPPO", "OPPO"), ("vivo", "vivo"), ("平安科技", "PingAn Tech"), ("顺丰科技", "SF Tech"),
        ("迅雷", "Xunlei"), ("创梦天地", "iDreamSky"), ("金蝶", "Kingdee"), ("微众银行", "Webank"),
        ("深信服", "Sangfor"), ("优必选", "UBTECH"), ("柔宇科技", "Royole"), ("碳云智能", "iCarbonX"),
        ("传音控股", "Transsion"), ("大族激光", "Han's Laser"), ("商汤深圳", "SenseTime SZ"),
        ("云天励飞", "Intellifusion")
    ]
}

positions = [
    ("前端开发工程师", "HTML/CSS/JavaScript, React/Vue, TypeScript, 响应式设计, 性能优化"),
    ("后端开发工程师", "Java/Python/Go, Spring Boot/Django, MySQL/PostgreSQL, Redis, 微服务架构"),
    ("全栈开发工程师", "前后端全栈, React+Node.js/Python, 数据库设计, DevOps, CI/CD"),
    ("iOS开发工程师", "Swift, Objective-C, UIKit/SwiftUI, Xcode, App Store发布流程"),
    ("Android开发工程师", "Kotlin, Java, Android SDK, Jetpack, Material Design"),
    ("算法工程师", "机器学习, 深度学习, PyTorch/TensorFlow, 数据建模, 特征工程"),
    ("数据工程师", "Python, SQL, Spark/Hadoop, ETL, 数据仓库, Airflow"),
    ("DevOps工程师", "Docker, Kubernetes, Jenkins, Linux, CI/CD, AWS/阿里云"),
    ("测试工程师", "自动化测试, Selenium/Appium, 性能测试, 接口测试, 测试框架设计"),
    ("产品经理", "需求分析, 原型设计, Axure/Figma, 数据驱动, 用户研究"),
    ("UI/UX设计师", "Figma/Sketch, 交互设计, 视觉设计, 设计系统, 用户体验研究"),
    ("安全工程师", "网络安全, 渗透测试, 安全审计, WAF, 加密算法, 安全合规"),
    ("大数据开发工程师", "Spark, Flink, Hive, Hadoop, Kafka, 数据湖"),
    ("云计算工程师", "AWS/阿里云/腾讯云, 虚拟化, 容器技术, 网络架构, 自动化运维"),
    ("游戏客户端开发", "Unity/Unreal, C#/C++, 游戏引擎, 图形渲染, 性能优化"),
    ("游戏服务端开发", "Go/C++, 分布式服务器, 网络编程, 数据库, 高并发"),
    ("嵌入式开发工程师", "C/C++, RTOS, 单片机, 驱动开发, 硬件调试"),
    ("AI产品经理", "AI应用场景, 大模型, Prompt Engineering, 数据标注, 算法理解"),
    ("技术项目经理", "项目管理, 敏捷开发, 风险控制, 跨团队协调, PMP/Scrum"),
    ("数据库管理员", "MySQL/PostgreSQL/Redis, 性能调优, 备份恢复, 高可用架构, 数据迁移")
]

salary_ranges = [
    "15K-25K", "18K-30K", "20K-35K", "25K-40K", "30K-50K",
    "12K-20K", "20K-30K", "15K-28K", "22K-38K", "25K-45K"
]

print("\n[2/3] Creating jobs...")
total = 0
now = int(time.time())

for city, comps in companies.items():
    print(f"  {city}: ", end="", flush=True)
    for i, (comp_cn, comp_en) in enumerate(comps):
        pos_name, reqs = positions[i % len(positions)]
        title = f"{comp_cn} - {pos_name}"
        salary = salary_ranges[i % len(salary_ranges)]
        desc = f"{comp_cn}（{comp_en}）招聘{pos_name}，工作地点{city}。我们正在寻找优秀的{pos_name}加入团队，共同打造行业领先的产品与服务。"
        full_reqs = f"{reqs}。工作地点：{city}。"
        vi = 1 if i % 3 == 0 else 0

        cur.execute(
            "INSERT INTO v2_jobs (user_id, title, description, requirements, salary_range, city, status, virtual_interview, ai_generated, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (existing_id, title, desc, full_reqs, salary, city, "open", vi, 1, now + total)
        )
        total += 1
    print("OK")

conn.commit()
conn.close()
print(f"\n[3/3] Done! Created {total} jobs total.")
