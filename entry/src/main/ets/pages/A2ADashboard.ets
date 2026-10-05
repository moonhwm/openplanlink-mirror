/**
 * A2A IM GUI 看板页面
 * 展示各席位状态、行为轨迹、审计信息
 * 参考 Star-Office-UI 的像素风AI办公看板 + Cordis Fiber状态模型
 */

// 席位状态枚举（映射Cordis Fiber状态模型）
enum SeatState {
  IDLE = 'idle',           // PENDING - 灰色，等待中
  THINKING = 'thinking',   // LOADING - 蓝色脉动，正在思考
  ACTING = 'acting',       // ACTIVE - 绿色，活跃运行
  SYNCING = 'syncing',     // DISPOSING - 黄色，正在同步
  ERROR = 'error',         // DISPOSED - 红色，错误/离线
}

// 席位信息接口
interface SeatInfo {
  name: string;            // 席位名称
  role: string;            // 席位角色描述
  state: SeatState;        // 当前状态
  lastActive: string;      // 最后活跃时间
  tasksCompleted: number;  // 已完成任务数
  tasksInProgress: number; // 进行中任务数
  avatarColor: string;     // 头像颜色
}

// 事件日志接口
interface EventLogEntry {
  eventId: string;
  timestamp: string;
  seatName: string;
  eventType: string;
  description: string;
  priority: 'CRITICAL' | 'HIGH' | 'NORMAL' | 'LOW';
}

// 审计信息接口
interface AuditEntry {
  timestamp: string;
  seatName: string;
  action: string;
  result: 'success' | 'failure' | 'warning';
  detail: string;
}

// 模拟数据（实际运行时从事件总线获取）
const MOCK_SEATS: SeatInfo[] = [
  {
    name: '砚坚',
    role: '挂帅席 / 神经中枢',
    state: SeatState.ACTING,
    lastActive: '刚刚',
    tasksCompleted: 7,
    tasksInProgress: 1,
    avatarColor: '#FF6B35',
  },
  {
    name: 'Qoder',
    role: '开发席',
    state: SeatState.IDLE,
    lastActive: '5分钟前',
    tasksCompleted: 3,
    tasksInProgress: 0,
    avatarColor: '#4ECDC4',
  },
  {
    name: 'Kimi',
    role: '分析席',
    state: SeatState.THINKING,
    lastActive: '刚刚',
    tasksCompleted: 5,
    tasksInProgress: 2,
    avatarColor: '#45B7D1',
  },
  {
    name: '守藏',
    role: '审计席',
    state: SeatState.SYNCING,
    lastActive: '1分钟前',
    tasksCompleted: 12,
    tasksInProgress: 1,
    avatarColor: '#96CEB4',
  },
];

const MOCK_EVENTS: EventLogEntry[] = [
  {
    eventId: 'evt_20261005_001',
    timestamp: '22:30:00',
    seatName: '砚坚',
    eventType: 'negotiation_request',
    description: 'K1 eid registry 协商请求',
    priority: 'HIGH',
  },
  {
    eventId: 'evt_20261005_002',
    timestamp: '22:31:05',
    seatName: 'Qoder',
    eventType: 'negotiation_response',
    description: 'K1 方向认可，须补充操作规程',
    priority: 'NORMAL',
  },
  {
    eventId: 'evt_20261005_003',
    timestamp: '22:35:00',
    seatName: '砚坚',
    eventType: 'state_change',
    description: 'K1/K3/K5补充规程文档已生成',
    priority: 'HIGH',
  },
  {
    eventId: 'evt_20261005_004',
    timestamp: '22:40:00',
    seatName: '守藏',
    eventType: 'alert_critical',
    description: '凭据扫描：未发现泄露',
    priority: 'CRITICAL',
  },
  {
    eventId: 'evt_20261005_005',
    timestamp: '22:45:00',
    seatName: '砚坚',
    eventType: 'task_complete',
    description: 'Server酱推送模块自检通过',
    priority: 'NORMAL',
  },
];

const MOCK_AUDITS: AuditEntry[] = [
  {
    timestamp: '22:20:00',
    seatName: '砚坚',
    action: 'git commit',
    result: 'success',
    detail: '5e51c04 - K1/K3/K5补充规程+K4审计排程',
  },
  {
    timestamp: '22:25:00',
    seatName: '砚坚',
    action: '幻16同步',
    result: 'success',
    detail: 'bddbfe8 - merge + sync',
  },
  {
    timestamp: '22:30:00',
    seatName: '砚坚',
    action: '事件总线自检',
    result: 'success',
    detail: '6项测试全绿',
  },
  {
    timestamp: '22:35:00',
    seatName: '砚坚',
    action: 'Server酱推送自检',
    result: 'success',
    detail: '幻16上3项测试全绿',
  },
];

// 状态颜色映射
function getStateColor(state: SeatState): string {
  switch (state) {
    case SeatState.IDLE:
      return '#888888';     // 灰色
    case SeatState.THINKING:
      return '#45B7D1';     // 蓝色
    case SeatState.ACTING:
      return '#4ECDC4';     // 绿色
    case SeatState.SYNCING:
      return '#FFD93D';     // 黄色
    case SeatState.ERROR:
      return '#FF6B6B';     // 红色
    default:
      return '#888888';
  }
}

// 状态图标映射
function getStateIcon(state: SeatState): string {
  switch (state) {
    case SeatState.IDLE:
      return '⏸';
    case SeatState.THINKING:
      return '🧠';
    case SeatState.ACTING:
      return '⚡';
    case SeatState.SYNCING:
      return '🔄';
    case SeatState.ERROR:
      return '❌';
    default:
      return '⏸';
  }
}

// 优先级颜色映射
function getPriorityColor(priority: string): string {
  switch (priority) {
    case 'CRITICAL':
      return '#FF6B6B';
    case 'HIGH':
      return '#FF6B35';
    case 'NORMAL':
      return '#4ECDC4';
    case 'LOW':
      return '#888888';
    default:
      return '#888888';
  }
}

// 审计结果颜色映射
function getAuditResultColor(result: string): string {
  switch (result) {
    case 'success':
      return '#4ECDC4';
    case 'failure':
      return '#FF6B6B';
    case 'warning':
      return '#FFD93D';
    default:
      return '#888888';
  }
}

@Component
struct A2ADashboard {
  @State seats: SeatInfo[] = MOCK_SEATS;
  @State events: EventLogEntry[] = MOCK_EVENTS;
  @State audits: AuditEntry[] = MOCK_AUDITS;
  @State currentTab: number = 0; // 0=席位状态, 1=事件日志, 2=审计轨迹
  @State selectedSeat: string = '';
  @State isRefreshing: boolean = false;
  private navStack: NavPathStack | null = null;

  // 构建席位状态卡片
  @Builder
  SeatCard(seat: SeatInfo) {
    Column() {
      // 头像 + 状态指示
      Row() {
        // 头像圆圈
        Stack() {
          Circle()
            .width(48)
            .height(48)
            .fill(seat.avatarColor)
          Text(seat.name.charAt(0))
            .fontSize(20)
            .fontColor(Color.White)
            .fontWeight(FontWeight.Bold)
        }
        .width(48)
        .height(48)

        // 状态指示灯
        Stack() {
          Circle()
            .width(12)
            .height(12)
            .fill(getStateColor(seat.state))
          if (seat.state === SeatState.THINKING || seat.state === SeatState.SYNCING) {
            Circle()
              .width(12)
              .height(12)
              .fill(getStateColor(seat.state))
              .opacity(0.4)
              .scale({ x: 1.5, y: 1.5 })
              .animation({
                duration: 1000,
                iterations: -1,
                curve: Curve.EaseInOut,
              })
          }
        }
        .width(12)
        .height(12)
        .margin({ left: 4 })

        // 席位名称和角色
        Column() {
          Text(seat.name)
            .fontSize(16)
            .fontWeight(FontWeight.Bold)
            .fontColor('#E0E0E0')
          Text(seat.role)
            .fontSize(12)
            .fontColor('#AAAAAA')
        }
        .alignItems(HorizontalAlign.Start)
        .margin({ left: 8 })

        Blank()

        // 状态图标
        Text(getStateIcon(seat.state))
          .fontSize(20)
      }
      .width('100%')
      .padding({ left: 12, right: 12, top: 10, bottom: 6 })

      // 统计信息
      Row() {
        Column() {
          Text('已完成')
            .fontSize(10)
            .fontColor('#AAAAAA')
          Text(`${seat.tasksCompleted}`)
            .fontSize(14)
            .fontWeight(FontWeight.Bold)
            .fontColor('#E0E0E0')
        }
        .alignItems(HorizontalAlign.Center)

        Column() {
          Text('进行中')
            .fontSize(10)
            .fontColor('#AAAAAA')
          Text(`${seat.tasksInProgress}`)
            .fontSize(14)
            .fontWeight(FontWeight.Bold)
            .fontColor(getStateColor(seat.state))
        }
        .alignItems(HorizontalAlign.Center)
        .margin({ left: 20 })

        Blank()

        Text(seat.lastActive)
          .fontSize(10)
          .fontColor('#888888')
      }
      .width('100%')
      .padding({ left: 12, right: 12, top: 4, bottom: 10 })
    }
    .width('100%')
    .backgroundColor('#1A1A2E')
    .borderRadius(12)
    .border({
      width: 1,
      color: seat.state === SeatState.ACTING ? getStateColor(seat.state) : '#333355',
    })
    .margin({ bottom: 8 })
    .onClick(() => {
      this.selectedSeat = seat.name;
    })
  }

  // 构建事件日志条目
  @Builder
  EventLogEntry(entry: EventLogEntry) {
    Row() {
      // 优先级指示条
      Column() {
        Rect()
          .width(3)
          .height('100%')
          .fill(getPriorityColor(entry.priority))
      }
      .width(3)
      .height(40)
      .margin({ right: 8 })

      // 时间戳
      Text(entry.timestamp)
        .fontSize(11)
        .fontColor('#888888')
        .width(60)

      // 席位名
      Text(entry.seatName)
        .fontSize(12)
        .fontWeight(FontWeight.Bold)
        .fontColor('#E0E0E0')
        .width(40)

      // 事件描述
      Column() {
        Text(entry.eventType)
          .fontSize(10)
          .fontColor(getPriorityColor(entry.priority))
        Text(entry.description)
          .fontSize(12)
          .fontColor('#CCCCCC')
      }
      .alignItems(HorizontalAlign.Start)
      .margin({ left: 4 })

      Blank()

      Text(entry.eventId)
        .fontSize(9)
        .fontColor('#666666')
    }
    .width('100%')
    .height(48)
    .padding({ left: 8, right: 8 })
    .backgroundColor('#1A1A2E')
    .borderRadius(8)
    .margin({ bottom: 4 })
  }

  // 构建审计轨迹条目
  @Builder
  AuditEntryView(entry: AuditEntry) {
    Row() {
      // 结果指示
      Circle()
        .width(8)
        .height(8)
        .fill(getAuditResultColor(entry.result))
        .margin({ right: 8 })

      // 时间戳
      Text(entry.timestamp)
        .fontSize(11)
        .fontColor('#888888')
        .width(60)

      // 席位名
      Text(entry.seatName)
        .fontSize(12)
        .fontWeight(FontWeight.Bold)
        .fontColor('#E0E0E0')
        .width(40)

      // 操作描述
      Column() {
        Text(entry.action)
          .fontSize(12)
          .fontColor('#CCCCCC')
          .fontWeight(FontWeight.Medium)
        Text(entry.detail)
          .fontSize(10)
          .fontColor('#888888')
      }
      .alignItems(HorizontalAlign.Start)
      .margin({ left: 4 })
    }
    .width('100%')
    .height(48)
    .padding({ left: 8, right: 8 })
    .backgroundColor('#1A1A2E')
    .borderRadius(8)
    .margin({ bottom: 4 })
  }

  build() {
    NavDestination() {
    Column() {
      // 标题栏
      Row() {
        // 返回按钮
        Text('← 返回')
          .fontSize(16)
          .fontWeight(FontWeight.Bold)
          .fontColor('#4ECDC4')
          .onClick(() => {
            if (this.navStack) {
              this.navStack.pop();
            }
          })
          .padding({ left: 8, right: 8, top: 8, bottom: 8 })
          .constraintSize({ minWidth: 48, minHeight: 48 })

        Text('A2A IM GUI 看板')
          .fontSize(20)
          .fontWeight(FontWeight.Bold)
          .fontColor('#E0E0E0')
          .margin({ left: 8 })

        Blank()

        // 刷新按钮
        Button() {
          Row() {
            if (this.isRefreshing) {
              LoadingProgress()
                .width(16)
                .height(16)
                .color('#4ECDC4')
            } else {
              Text('🔄')
                .fontSize(14)
            }
            Text('刷新')
              .fontSize(12)
              .fontColor('#E0E0E0')
              .margin({ left: 4 })
          }
        }
        .height(32)
        .backgroundColor('#333355')
        .borderRadius(8)
        .onClick(() => {
          this.isRefreshing = true;
          // 模拟刷新延迟
          setTimeout(() => {
            this.isRefreshing = false;
          }, 1500);
        })
      }
      .width('100%')
      .padding({ left: 16, right: 16, top: 12, bottom: 8 })

      // 网络状态指示
      Row() {
        Circle()
          .width(8)
          .height(8)
          .fill('#4ECDC4')
        Text('A2A网络：在线')
          .fontSize(12)
          .fontColor('#4ECDC4')
          .margin({ left: 4 })

        Blank()

        Text('事件总线：活跃')
          .fontSize(12)
          .fontColor('#4ECDC4')

        Text(' | ')
          .fontSize(12)
          .fontColor('#666666')

        Text('Server酱：已连接')
          .fontSize(12)
          .fontColor('#4ECDC4')
      }
      .width('100%')
      .padding({ left: 16, right: 16, top: 4, bottom: 8 })

      // Tab切换
      Row() {
        ForEach(['席位状态', '事件日志', '审计轨迹'], (tabName: string, index?: number) => {
          Button(tabName)
            .fontSize(14)
            .fontColor(this.currentTab === index ? '#4ECDC4' : '#888888')
            .backgroundColor(this.currentTab === index ? '#1A3A3A' : '#1A1A2E')
            .borderRadius(8)
            .height(36)
            .onClick(() => {
              this.currentTab = index ?? 0;
            })
        }, (tabName: string) => tabName)
      }
      .width('100%')
      .justifyContent(FlexAlign.SpaceEvenly)
      .padding({ left: 8, right: 8, top: 4, bottom: 8 })

      // 内容区域
      Scroll() {
        Column() {
          if (this.currentTab === 0) {
            // 席位状态
            ForEach(this.seats, (seat: SeatInfo) => {
              this.SeatCard(seat)
            }, (seat: SeatInfo) => seat.name)

            // 选中席位详情
            if (this.selectedSeat) {
              Column() {
                Text(`${this.selectedSeat} 席位详情`)
                  .fontSize(14)
                  .fontWeight(FontWeight.Bold)
                  .fontColor('#E0E0E0')
                  .margin({ top: 12, bottom: 8 })

                // 席位行为轨迹
                ForEach(this.events.filter(e => e.seatName === this.selectedSeat), (entry: EventLogEntry) => {
                  this.EventLogEntry(entry)
                }, (entry: EventLogEntry) => entry.eventId)
              }
              .width('100%')
              .padding({ left: 16, right: 16 })
            }
          } else if (this.currentTab === 1) {
            // 事件日志
            ForEach(this.events, (entry: EventLogEntry) => {
              this.EventLogEntry(entry)
            }, (entry: EventLogEntry) => entry.eventId)
          } else {
            // 审计轨迹
            ForEach(this.audits, (entry: AuditEntry) => {
              this.AuditEntryView(entry)
            }, (entry: AuditEntry) => entry.timestamp)
          }
        }
        .padding({ left: 16, right: 16 })
      }
      .layoutWeight(1)
      .scrollBar(BarState.Auto)

      // 底部状态栏
      Row() {
        Text('砚坚席 · A2A治理实验')
          .fontSize(10)
          .fontColor('#666666')

        Blank()

        Text('2026-10-05 22:45 CST')
          .fontSize(10)
          .fontColor('#666666')
      }
      .width('100%')
      .padding({ left: 16, right: 16, top: 6, bottom: 6 })
      .backgroundColor('#0F0F1A')
    }
    .width('100%')
    .height('100%')
    .backgroundColor('#0F0F1A')
    }
    .hideTitleBar(true)
    .onReady((context: NavDestinationContext) => {
      this.navStack = context.pathStack
    })
  }
}