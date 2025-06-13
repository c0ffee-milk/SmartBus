// 引入二维码生成库
import drawQrcode from '../../../utils/weapp.qrcode.min.js'

const app = getApp()
const baseUrl = app.globalData.baseUrl

Page({
  data: {
    reservationDetail: {
      id: '', // 预约ID
      schedule_id: '', // 班次ID
      seat_number: '', // 座位号
      status: '', // 预约状态
      reserved_at: '', // 预约时间
      qr_code: '' // 预约二维码
    },
    qrcodePath: '' // 二维码临时路径
  },

  onLoad(options) {
    const { id } = options;
    // 先显示骨架屏或加载状态
    this.setData({ isLoading: true });
    this.getReservationDetail(id);
  },

  getReservationDetail(id) {
    wx.request({
      url: `${baseUrl}/reservations/detail`,
      method: 'GET',
      header: {
        'Authorization': 'Bearer ' + app.globalData.accessToken,
        'Content-Type': 'application/json'
      },
      data: { id },
      success: (res) => {
        if (res.data) {
          console.log('获取数据成功:', res.data);
          this.setData({ 
            reservationDetail: {
              id: res.data.id,
              schedule_id: res.data.schedule_id,
              seat_number: res.data.seat_number,
              status: res.data.status,
              reserved_at: res.data.reserved_at,
              qr_code: res.data.qr_code
            }
          }, () => {
            this.generateQRCode(); // 数据加载完成后生成二维码
          });
        } else {
          console.error('返回数据为空');
        }
      },
      fail: (err) => {
        console.error('请求失败:', err);
      }
    });
  },

  // 生成二维码
  generateQRCode() {
    const qrCodeText = this.data.reservationDetail.qr_code || 'https://example.com';
    drawQrcode({
      width: 170,
      height: 170,
      canvasId: 'qrcodeCanvas',
      text: qrCodeText,
      callback: () => {
        wx.canvasToTempFilePath({
          canvasId: 'qrcodeCanvas',
          success: (res) => {
            this.setData({ qrcodePath: res.tempFilePath })
          },
          fail: (err) => {
            console.error('生成二维码失败:', err)
          }
        }, this)
      }
    })
  },

  // 保存二维码到相册
  saveQRCode() {
    wx.saveImageToPhotosAlbum({
      filePath: this.data.qrcodePath,
      success: () => wx.showToast({ title: '保存成功' }),
      fail: () => wx.showToast({ title: '保存失败', icon: 'error' })
    })
  }
});

