// config/common.js
export const USER_PAGE = {
    studentTabbarList: [
      // 普通用户菜单
      {
        "pagePath": "/pages/index/index",
        "text": "班车预约",
        "iconPath": "/images/VehicleBus.png",
        "selectedIconPath": "/images/Selected_VehicleBus.png"
      },
      {
        "pagePath": "/pages/reservation/reservation-list/reservation-list",
        "text": "我的预约",
        "iconPath": "/images/reserve.png",
        "selectedIconPath": "/images/reserve.png"
      },
      {
        "pagePath": "/pages/mines/mines", 
        "text": "我的",
        "iconPath": "/images/mine.png",
        "selectedIconPath": "/images/Selected_mine.png"
      }
    ],
    teacherTabbarList: [
      // 普通用户菜单
      {
        "pagePath": "/pages/index/index",
        "text": "班车预约",
        "iconPath": "/images/VehicleBus.png",
        "selectedIconPath": "/images/Selected_VehicleBus.png"
      },
      {
        "pagePath": "/pages/reservation/reservation-list/reservation-list",
        "text": "我的预约",
        "iconPath": "/images/reserve.png",
        "selectedIconPath": "/images/reserve.png"
      },
      {
        "pagePath": "/pages/mines/mines", 
        "text": "我的",
        "iconPath": "/images/mine.png",
        "selectedIconPath": "/images/Selected_mine.png"
      }
    ],
    adminTabbarList: [
      // 管理员菜单
      {
        "pagePath":"/pages/admin/orders/orders",
        "text":"班次情况",
        "iconPath": "/images/VehicleBus.png",
        "selectedIconPath": "/images/Selected_VehicleBus.png"
      },
      {
        "pagePath":"/pages/admin/admin-mines/admin-mines",
        "text":"管理",
        "iconPath":"/images/manager.png",
        "selectedIconPath":"/images/manager_selected.png"
      }
      
    ],
    driverTabbarList: [
      // 司机菜单
      {
        "pagePath": "/pages/driver/scan/scan",
        "text": "扫码",
        "iconPath": "/images/scan.png",
        "selectedIconPath": "/images/scan.png"
      },
      {
        "pagePath": "/pages/driver/driver-list/driver-list",
        "text": "司机",
        "iconPath": "/images/driver.png",
        "selectedIconPath": "/images/driver_selected.png"
      }
    ]
  };