// pages/mines/mines.js

const app = getApp() // 获取全局应用实例对象

Page({
  
  // 在onShow生命周期中添加认证检查
  onShow: function() {
      if (typeof this.getTabBar === 'function' && this.getTabBar()) {
          this.getTabBar().setData({
              selected: 2
          });
      }
      // 调试日志
      console.log('当前accessToken:', app.globalData.accessToken);
      // 新增：检查用户是否认证，未认证则自动弹出认证窗口
      if (!app.globalData.accessToken) {
          console.log('检测到未认证，触发认证流程');
          this.checkAuthentication();
      }
  },
  
  data: {
    userName : null,
    userCard : null,
    userRole : null,
    showInputModal: false,
    code : null, // 登录码，用于获取用户信息
  },
  
  onLoad() {
    const userName = app.globalData.userInfo?.name || null; 
    const userCard = app.globalData.userInfo?.school_id || null; 
    const userRole = app.globalData.userInfo?.role || null; 
    this.setData({ userName, userCard, userRole });
  },

  navigateToReservationList() {
    wx.switchTab({
      url: '/pages/reservation/reservation-list/reservation-list',
      fail: (err) => {
        console.error('跳转失败', err);
      }
    });
  },

  navigateToReservationNotice() {
    wx.navigateTo({
      url: '/pages/reservation/reservation-notice/reservation-notice',
      fail: (err) => {
        console.error('跳转失败', err);
      }
    });
  },

  hideInputModal() {
    this.setData({
      showInputModal: false
    });
  },


  checkAuthentication: function() {
      console.log('执行认证检查，当前showInputModal值:', this.data.showInputModal);
      if (!app.globalData.accessToken) {
          this.setData({
              showInputModal: true
          }, () => {
              console.log('设置showInputModal为true后:', this.data.showInputModal);
          });
          wx.login({
              success: (res) => {
                  if (res.code) {
                      this.setData({ code: res.code });
                  } else {
                      console.error('登录失败！' + res.errMsg);
                      wx.showToast({
                          title: '登录失败，请重试',
                          icon: 'none'
                      });
                  }
              }
          });
      }
  },

  confirmInput(e) {
    const { name, card } = e.detail;
    const code = this.data.code;
    const baseUrl = app.globalData.baseUrl;

    if (!name || !card) {
      console.error('请输入姓名和学号');
      wx.showToast({
        title: '请输入姓名和学号',
        icon: 'none',
      });
    }

    if (!code) {
      console.error('未获取到登录码，请重试');
      wx.showToast({
        title: '认证失败，请重试',
        icon: 'none',
      });
      return;
    }

    // 调用后端接口进行认证
    wx.request({
      url: `${baseUrl}/auth/login`,
      method: 'POST',
      data: {
        code: code,
        name: name,
        school_id: card
      },
      success: (res) => {
        console.log(res);
        app.globalData.accessToken = res.data.access_token;
        app.globalData.userInfo = res.data;
        console.log(app.globalData);
        this.setData({ userName: res.data.user.name, userCard: res.data.user.school_id, userRole: res.data.user.role });
        
        // 修改：认证成功后重置页面
        if (typeof this.getTabBar === 'function' && this.getTabBar()) {
            this.getTabBar().updateTabbarList();
            // 根据角色跳转到对应首页
            if(res.data.user.role === 'driver') {
                wx.switchTab({ url: '/pages/driver/driver-list/driver-list' });
            } else if(res.data.user.role === 'admin') {
                wx.switchTab({ url: '/pages/admin/admin-mines/admin-mines' });
            } else {
                wx.switchTab({ url: '/pages/index/index' });
            }
        }
        console.log('accessToken:', app.globalData.accessToken);
        wx.showToast({
          title: '认证成功',
          icon: 'success',
        });
        this.setData({
          showInputModal: false
        });
      },
      fail: (err) => {
        console.error('请求失败:', err);
        wx.showToast({
          title: '认证失败，请重试',
          icon: 'none',
        });
      }
    });
  },
});