# 智慧校园班车预约微信小程序 (SmartBus)

## 🚀 项目概述

“智慧校园班车预约微信小程序”（SmartBus）旨在为现代智慧校园提供一套高效、便捷的班车预约与管理解决方案。该系统通过微信小程序作为用户端入口，结合强大的后端API服务，实现了学生、教职工、司机和管理员等多角色的班车预约、乘车签到、班次管理及数据统计等核心功能。项目以提升校园班车服务的智能化水平和用户体验为目标，致力于优化资源配置，缓解高峰期压力，并为校园交通管理提供科学决策支持。

## ✨ 核心优势与创新亮点

SmartBus项目不仅实现了班车预约的基础功能，更在以下几个方面展现了其独特的优势和创新性，旨在提供更智能、高效、人性化的班车服务：

### 1. 🧠 AI赋能智能调度辅助决策

本项目的一大核心创新在于引入了人工智能辅助决策能力。通过集成大型语言模型（LLM）服务，系统能够对班车运营数据进行深度分析，并为管理员提供科学、具体的班次调度优化建议。这极大地提升了班车运营的智能化水平和资源利用效率。

**技术实现亮点：**

* **`services/ai_service.py` 模块：** 该模块封装了与AI模型的交互逻辑，`get_analysis` 方法能够接收统计数据，并生成针对性的调度建议。例如，根据班次的预约数、签到数、上座率等指标，AI可以建议增加或减少班次、调整发车时段、优化座位容量等。

  ```python
  # 示例代码片段 (services/ai_service.py)
  class AIService:
      def get_analysis(self, statistics, start_date_str, end_date_str):
          # ... 构建Prompt，调用LLM API ...
          completion = self.client.chat.completions.create(
              model="qwen-turbo", # 可配置为其他LLM模型
              messages=[
                  {"role": "system", "content": "你是一个专业的班次调度顾问，请根据数据提供具体的调度建议。"},
                  {"role": "user", "content": prompt}
              ],
              temperature=0.1,
              max_tokens=1000
          )
          suggestions = completion.choices[0].message.content.strip()
          return suggestions
  ```

* **数据驱动决策：** 管理员不再依赖经验判断，而是基于AI分析的客观数据和建议进行决策，有效缓解了高峰期压力，提升了整体服务质量和乘客满意度。

### 2. 👥 精细化多角色管理与权限控制

系统针对校园内不同用户群体（学生/教职工、司机、管理员）设计了精细化的角色管理和权限控制机制，确保了系统操作的规范性和数据安全性。

**技术实现亮点：**

* **`model.py` 中的 `RoleEnum`：** 清晰定义了系统中的所有角色类型，为权限管理提供了基础。

  ```python
  # 示例代码片段 (model.py)
  class RoleEnum(enum.Enum):
      admin = 'admin'
      teacher = 'teacher'
      student = 'student'
      driver = 'driver'
      temp = 'temp'
  ```

* **基于JWT的权限校验：** 后端使用 `Flask-JWT-Extended` 实现基于JSON Web Token (JWT) 的身份认证和权限管理。例如，`routes/admin.py` 中的 `@admin_required` 装饰器确保只有具备管理员权限的用户才能访问敏感的管理接口，有效防止了未授权操作。

  ```python
  # 示例代码片段 (routes/admin.py)
  def admin_required(fn):
      @jwt_required()
      def wrapper(*args, **kwargs):
          current_user_id = get_jwt_identity()
          user = User.query.get(current_user_id)
          if not user or user.role != RoleEnum.admin:
              return jsonify({'error': '需要管理员权限'}), 403
          return fn(*args, **kwargs)
      wrapper.__name__ = fn.__name__
      return wrapper
  ```

* **前端动态适配：** 微信小程序前端根据用户的角色动态调整Tab Bar和功能入口，为不同角色提供定制化的操作界面，提升了用户体验的直观性和便捷性。

### 3. 🔄 完善的预约与签到闭环及惩罚机制

项目构建了从班次查询、在线预约、生成二维码到司机扫码签到、标记缺席的完整闭环流程，并引入了有效的惩罚机制，确保了班车预约服务的规范化、高效化和公平性。

**技术实现亮点：**

* **实时座位与教师优先：** `routes/reservation.py` 中的 `create_reservation` 函数在处理预约请求时，会实时检查班次剩余座位，并特别考虑教师优先预约的业务逻辑，体现了人性化服务。

  ```python
  # 示例代码片段 (routes/reservation.py)
  if current_reservations >= schedule.dynamic_capacity:
      return jsonify({'error': '该班次已满'}), 400
  
  is_teacher = user.role == RoleEnum.teacher
  if not is_teacher and current_reservations >= (schedule.dynamic_capacity - TEACHER_PRIORITY_SEATS):
      return jsonify({'error': '该班次仅剩教师优先座位'}), 400
  ```

* **唯一二维码签到：** 每个预约成功后都会生成一个唯一的二维码 (`qr_code = str(uuid.uuid4())`)，司机通过扫描此二维码即可完成签到，有效防止了冒用和虚假签到，确保了签到的准确性和便捷性。

* **缺席惩罚机制：** 对于恶意取消或未签到的用户，系统会自动记录惩罚，并在一定期限内（`PENALTY_DAYS = 7`）限制其再次预约，有效约束了用户行为，减少资源浪费，保障了其他用户的公平预约权益。

### 4. ⚡ 高性能与高可用架构设计

为应对校园班车预约可能出现的瞬时高并发场景，系统在技术选型和架构设计上充分考虑了性能和可用性，确保了系统的高响应速度和稳定性。

**技术实现亮点：**

* **Redis缓存机制：** 广泛使用Redis作为内存数据存储，对可用班次列表、用户预约记录、管理员班次列表以及数据导出结果等高频访问数据进行多层缓存。这显著减少了数据库查询压力，大幅提升了系统响应速度和并发处理能力。

  ```python
  # 示例代码片段 (routes/reservation.py)
  cached_data = redis_client.get(cache_key)
  if cached_data:
      return jsonify(json.loads(cached_data))
  ```

* **缓存更新策略：** 通过 `cache.py` 中的 `cache_manager` 实现了智能的缓存更新和失效机制，确保了缓存数据与数据库数据的一致性，避免了脏读问题。

### 5. 📱 友好的用户体验与跨平台支持

*   **微信小程序原生开发：** 充分利用微信小程序生态，用户无需下载额外App，即可通过微信快速访问和使用，降低了用户门槛，符合当前移动互联网的使用习惯。
*   **直观的界面设计：** 界面设计遵循简洁、直观的原则，采用微信小程序官方组件库，确保用户体验的统一性和流畅性。关键信息如班次时间、剩余座位、预约状态等都清晰展示，降低了用户的学习成本。
*   **自定义组件与动态适配：** 前端采用了自定义Tab Bar和导航栏组件，使得界面更具个性化和品牌识别度。同时，根据用户角色动态调整功能入口和界面布局，为不同角色提供了定制化的操作体验。

## 🛠️ 技术栈

### 前端

*   **微信小程序原生开发：** WXML, WXSS, JavaScript
*   **组件化开发：** 自定义Tab Bar, 导航栏, 输入弹窗等

### 后端

*   **Python 3.x**
*   **Flask：** 轻量级Web框架
*   **SQLAlchemy：** ORM框架，用于数据库操作
*   **Flask-JWT-Extended：** JWT认证与权限管理
*   **Redis：** 内存数据存储与缓存
*   **SQLite：** 轻量级关系型数据库 (开发/测试环境，可切换为MySQL/PostgreSQL)
*   **qrcode：** 二维码生成
*   **pandas, openpyxl：** 数据处理与Excel导出
*   **logging：** 日志记录
*   **OpenAI/通义千问 API：** AI服务集成

## 📊 数据库设计

主要实体关系图（基于 `model.py`）：

*   **User (用户)**
*   **Route (路线)**
*   **Schedule (班次)**
*   **Reservation (预约)**
*   **Penalty (惩罚)**
*   **DriverSchedule (司机排班)**

## 🚀 安装与运行

### 前端 (微信小程序)

1.  **下载项目代码：** 将 `SmartBus/front` 目录下的代码下载到本地。
2.  **微信开发者工具：** 使用微信开发者工具打开 `SmartBus/front` 目录。
3.  **配置API地址：** 在 `SmartBus/front/config/common.js` 中配置后端API的地址。
4.  **预览与调试：** 在开发者工具中进行预览、调试和上传。

### 后端 (Flask)

1. **下载项目代码：** 将 `SmartBus/back` 目录下的代码下载到本地。

2. **创建Python虚拟环境 (推荐)：**

   ```bash
   python3 -m venv venv
   source venv/bin/activate  # Linux/macOS
   # venv\Scripts\activate   # Windows
   ```

3. **安装依赖：**

   ```bash
   pip install -r requirements.txt
   ```

4. **配置环境变量：**

   *   设置 `FLASK_APP=app.py`
   *   设置 `FLASK_ENV=development` (开发环境)
   *   配置 `JWT_SECRET_KEY` 和 `REDIS_URL` 等，具体请参考 `config.py`。
   *   配置AI服务相关API Key，例如 `OPENAI_API_KEY` 或通义千问的API Key。

5. **初始化数据库：**

   ```bash
   flask db init
   flask db migrate
   flask db upgrade
   ```

   （如果使用SQLite，数据库文件 `shuttle_bus.db` 会在 `instance` 目录下生成）

6. **运行后端服务：**

   ```bash
   flask run
   # 或者使用 gunicorn 等生产级WSGI服务器
   # gunicorn -w 4 -b 0.0.0.0:5000 app:app
   ```

## 💡 使用指南

1.  **用户注册与登录：** 用户首次使用需通过微信登录并进行身份认证（学号/工号）。
2.  **班车预约：** 在首页选择日期、起点、终点，浏览班次列表，点击“预约”按钮完成预约。
3.  **查看预约：** 在“我的预约”页面查看所有预约记录及详情。
4.  **乘车签到：** 司机登录后，进入司机端，点击“扫码签到”扫描乘客二维码。
5.  **后台管理：** 管理员登录后，可进行班次管理、用户管理、数据导出及查看AI调度建议。

## 🔮 未来展望

*   **消息通知：** 集成微信小程序消息推送，实现预约成功、班次变动、签到提醒等通知，提升用户体验。
*   **地图集成：** 在小程序中集成地图功能，直观展示班车路线、实时位置，方便用户规划行程。
*   **评价反馈：** 增加用户对班车服务、司机服务的评价功能，为服务质量改进提供依据。
*   **多语言支持：** 考虑未来国际化需求，支持多语言界面，扩大应用范围。
*   **数据可视化：** 进一步优化管理员后台的数据统计展示，提供更丰富的图表和分析维度，辅助更精准的运营决策。
*   **智能排班：** 引入更高级的智能排班算法，实现司机和车辆的自动化优化调度，进一步提升运营效率。

## 🤝 贡献

欢迎对本项目进行贡献！如果您有任何建议或发现Bug，请提交Issue或Pull Request。

## 📄 许可证

本项目采用 [MIT License](LICENSE) 开源。




