import { USER_PAGE } from "../config/common"  // 导入配置常量

Component({
    data: {
        selected: 0,  // 当前选中项索引
        color: "#7A7E83",  // 默认颜色
        selectedColor: "#3cc51f",  // 选中颜色
        list: []  // 导航菜单列表
    },
    
    // 组件生命周期函数
    attached() {
        this.updateTabbarList();  // 初始化加载菜单
    },

    methods: {
        // 切换标签页
        switchTab(e) {
            const data = e.currentTarget.dataset;
            const url = data.path;
            wx.switchTab({ url });
            this.setData({
                selected: data.index
            });
        },

        // 新增：角色变更时更新tabBar
        onRoleChange() {
            this.updateTabbarList();
            this.setData({
                selected: 0  // 重置选中项
            });
        },

        // 更新导航菜单列表
        updateTabbarList() {
            const role = getApp().globalData.userInfo?.user.role || 'student';
            console.log('当前角色:', role);
            this.setData({ 
                list: USER_PAGE[`${role}TabbarList`] || []
            });
        }
    }
});