var XLD_t = new Array(11).fill(null);
var XLD_q = new Array(11).fill(null);
var SMX_t = new Array(7).fill(null);
var SMX_q = new Array(7).fill(null);
var XLD = {};
var SMX = {};
var WlFldContr_XLD;
var WlReg_XLD;
var volWatSupply;
let chart1, chart2;



// 获取所有的输入框
const inputs_all = document.querySelectorAll('input[type="number"]');

inputs_all.forEach(input => {
    if (input.id) {
        // 当输入框的值改变时，把新的值存储到localStorage
        input.addEventListener('change', function () {
            localStorage.setItem(this.id, this.value);
        });

        // 当光标移动到输入框内时，从localStorage获取上次输入的值，并显示一个提示
        input.addEventListener('focus', function () {
            const lastValue = localStorage.getItem(this.id);
            if (lastValue) {
                this.placeholder = `${lastValue}`;
            }
        });

        // 当输入框失去焦点时，清空placeholder的值
        input.addEventListener('blur', function () {
            this.placeholder = '';
        });
    }
});

//定义一个函数，该函数接收xx,yy两个数组和x一个数值，返回y,首先找到xx中距离x最近的两个数，然后用这两个数对应的yy值进行线性插值
function interpolate(xx, yy, x) {
  //如果x大于等于xx中最后一个数，则返回yy中最后一个数
  if (x >= xx[xx.length - 1]) {
    return yy[yy.length - 1];
  }
  var i = 0;
  while (xx[i] <= x) {
    i++;
  }
  var x1 = xx[i - 1];
  var x2 = xx[i];
  var y1 = yy[i - 1];
  var y2 = yy[i];
  return y1 + (y2 - y1) * (x - x1) / (x2 - x1);
}

//定义一个名为CalculateT的函数，计算达到指定净出流水量所需的时间
function CalculateT(volTarg, tt, qq, iLastKeyP, iReservoir, dischargeMod) {
  var t2 = 0;
  if (iReservoir === 1) {
        var t1 = XLD_t[iLastKeyP - 1];
        //-------假设两个tt之间的qq是线性变化，计算tt[0]时刻到t1时刻XLD的入库水量------
        //找到t1之前tt中最近的时间的下标
        var i = 0;
        while (tt[i] < t1) {
            i++;
        }
        //从tt[0]到tt[i-1]对qq积分
        var vol = 0;
        for (var j = 0; j < i - 1; j++) {
            vol -= (tt[j + 1] - tt[j]) * (qq[j + 1] + qq[j]) / 2;
        }
        //插值得到t1时刻的qq
        var q1 = interpolate(tt, qq, t1);
        //vol加上从tt[i-1]到t1的qq积分
        vol -= (t1 - tt[i - 1]) * (q1 + qq[i - 1]) / 2;
        //vol = vol*3600;
        //-------------------------------------------------------------------------


        for (var j = 0; j < iLastKeyP - 1; j++) {
            vol += (XLD_t[j + 1] - XLD_t[j]) * (XLD_q[j + 1] + XLD_q[j]) / 2;
        }

        t2 = t1;
        var q2 = q1;
        var dt = 12;
        var stop_flag = 0;
        while (stop_flag === 0) {
            t2 = t2 + dt;
            q2 = interpolate(tt, qq, t2);
            vol -= dt * (q2 + q1) / 2;
            if (dischargeMod === 1) {
                //维持上一个调控流量
                vol += dt * XLD_q[iLastKeyP - 1];
                t1 = t2;
                q1 = q2;
                if (vol * 3600 / 10 ** 8 > volTarg) {
                    stop_flag = 1;
                }
                console.log('vol:', vol * 3600 / 10 ** 8);
            }
           else {
                //线性变化至当前调控流量
                var dVol = (t2 - XLD_t[iLastKeyP - 1]) * (XLD_q[iLastKeyP - 1] + XLD_q[iLastKeyP]) / 2;
                if ((vol + dVol) * 3600 / 10 ** 8 > volTarg) {
                    stop_flag = 1;
                }
                console.log('vol:', (vol + dVol) * 3600 / 10 ** 8);
            }            
        }
    } else if (iReservoir === 2) {
        var t1 = SMX_t[iLastKeyP - 1];
        var i = 0;
        while (tt[i] < t1) {
            i++;
        }

        var tStart = SMX_t[1];     //三门峡开始调度的时间，在此之前进出平衡
        var iStart = 0;
        //寻找落入调度时间范围的第一个入库数据点
        while (tt[iStart] < tStart) {
            iStart++;
        }

        var vol = 0;
        //计算从tStart到tt[iStart - 1]的入库水量
        var qStart = interpolate(tt, qq, tStart);
        vol -= (tt[iStart] - tStart) * (qStart + qq[iStart]) / 2;

        for (var j = iStart; j < i - 1; j++) {
            vol -= (tt[j + 1] - tt[j]) * (qq[j + 1] + qq[j]) / 2;
        }
        q1 = interpolate(tt, qq, t1);
        vol -= (t1 - tt[i - 1]) * (q1 + qq[i - 1]) / 2;
        vol += (SMX_t[2] - SMX_t[1]) * (SMX_q[2] + qStart) / 2;
        for (var j = 2; j < iLastKeyP - 1; j++) {
            vol += (SMX_t[j + 1] - SMX_t[j]) * (SMX_q[j + 1] + SMX_q[j]) / 2;
        }

        t2 = t1;
        var q2 = q1;
        var dt = 6;
        var stop_flag = 0;
        while (stop_flag === 0) {
            t2 = t2 + dt;
            q2 = interpolate(tt, qq, t2);
            vol -= dt * (q2 + q1) / 2;
            vol += dt * SMX_q[iLastKeyP - 1];
            t1 = t2;
            q1 = q2;

            if (iLastKeyP === 5) {
                if (vol * 3600 / 10 ** 8 < volTarg) {
                    stop_flag = 1;
                }
            } else {
                if (vol * 3600 / 10 ** 8 > volTarg) {
                    stop_flag = 1;
                }
            }
        }
    }
  return t2;
}

//计算开始回蓄的时间
function CalculateRefillT(volChange, tt, qq, ttNat, qqNat, tCtrl, qCtrl) {
  var qqCopy = qq.slice();
  
  //ttNat与qqNat是天然来流过程
  var t = 0;
  
  //ttNat是递增的，找出其中小于tt[1]的最后一个值的下标
  var i = 0;
  while (ttNat[i] < tt[1]) {
    i++;
  }
  //在ttNat[i-1]和ttNat[i]之间对qqNat插值得到tt[1]时刻的流量
  var q1 = interpolate(ttNat, qqNat, tt[1]);
  //找出ttNat中大于tt[0]的第一个值的下标
  var j = 0;
  while (ttNat[j] < tt[0]) {
    j++;
  }
  //在ttNat[j-1]和ttNat[j]之间对qqNat插值得到tt[0]时刻的流量
  var q0 = interpolate(ttNat, qqNat, tt[0]);
  //计算从tt[0]到tt[1]的入库水量，这两时刻间的流量使用qqNat中对应时刻的流量
  var vol_in = (ttNat[j] - tt[0]) * (q0 + qqNat[j]) / 2;
  //将ttNat[j]到ttNat[i-1]的入库水量累加到vol
  for (var k = j; k < i - 1; k++) {
    vol_in += (ttNat[k + 1] - ttNat[k]) * (qqNat[k + 1] + qqNat[k]) / 2;
  }
  
  vol_in += (tt[1] - ttNat[i - 1]) * (q1 + qqNat[i - 1]) / 2;
  
  //在ttNat和qqNat上插值计算tt[1]时刻对应的qq[1]
  qqCopy[1] = interpolate(ttNat, qqNat, tt[1]);

  //将tt[1]到tt[6]的入库水量累加到vol，注意qq[6]是null，tt[5]和tt[6]相等
  for (var k = 1; k < 5; k++) {
    vol_in += (tt[k + 1] - tt[k]) * (qqCopy[k + 1] + qqCopy[k]) / 2;
  }

  //如果tt[6]>tCtrl最后时刻，则弹窗提示，否则将tt[6]到tCtrl最后时刻的入库水量累加到vol
  if (tt[6] > tCtrl[tCtrl.length - 1]) {
    alert('三门峡最后时刻大于小浪底最大调度时刻，请重新输入');
  } else {
    //tt[6]到tCtrl最后时刻的入库水量都用qqNat中对应时刻的流量
    //先找到ttNat中大于tt[6]的第一个值的下标
    var k = 0;
    while (ttNat[k] < tt[6]) {
      k++;
    }
    //在ttNat[k-1]和ttNat[k]之间对qqNat插值得到tt[6]时刻的流量
    var q6 = interpolate(ttNat, qqNat, tt[6]);
    //将tt[6]到ttNat[k]间的入库水量累加到vol
    vol_in += (ttNat[k] - tt[6]) * (q6 + qqNat[k]) / 2;
    //找到ttNat中小于tCtrl最后时刻的最后一个值的下标
    var k2 = ttNat.length - 1;
    while (ttNat[k2] > tCtrl[tCtrl.length - 1]) {
      k2--;
    }
    //将ttNat[k]到ttNat[k2]的入库水量累加到vol
    for (var k = k; k < k2; k++) {
      vol_in += (ttNat[k + 1] - ttNat[k]) * (qqNat[k + 1] + qqNat[k]) / 2;
    }
    //在ttNat[k2]和ttNat[k2+1]之间对qqNat插值得到tCtrl最后时刻的流量
    var qEnd = interpolate(ttNat, qqNat, tCtrl[tCtrl.length - 1]);
    //将ttNat[k2]到tCtrl最后时刻的入库水量累加到vol
    vol_in += (tCtrl[tCtrl.length - 1] - ttNat[k2]) * (qEnd + qqNat[k2]) / 2;
  }

  var vol_out = 0;
  var iPre = 8;    //也许改为tCtrl.length-4更通用？
  for (var j = 1; j < iPre; j++) {
    vol_out += (tCtrl[j] - tCtrl[j - 1]) * (qCtrl[j] + qCtrl[j - 1]) / 2;
  }
  vol_out = volChange * 10 **8 / 3600 + vol_in - vol_out;
  var tPre = tCtrl[iPre - 1];
  var qPre = qCtrl[iPre - 1];
  var qCurrent = qCtrl[iPre];
  var tNext = tCtrl[iPre + 2];
  var qNext = (qCtrl[iPre + 2] + qCtrl[iPre + 1]) / 2;
  //求解vol_out = (t - tPre) * (qPre + qCurrent) / 2 + (tNext - t) * qNext
  t = (vol_out + (qCurrent + qPre) * tPre / 2 - qNext * tNext) / ((qCurrent + qPre) /2 - qNext); 

  return t;
}

window.onload = function() {
//弹出一个提示框
alert('这是第2版');


// Fetch the JSON data for Xiaolangdi
fetch('Xiaolangdi.json')
  .then(response => response.json())
  .then(data => {
    XLD = data;
    // Get the first chart area
    var ctx = document.getElementById('chartArea1').getContext('2d');

    // Create the chart
    chart1 = new Chart(ctx, {
      type: 'line',
      data: {
        labels: XLD.t,
        datasets: [
          {
            label: 'Inflow',
            data: XLD.Inflow,
            yAxisID: 'yAxis1',
          },
          {
            label: 'Outflow',
            data: XLD.Outflow,
            yAxisID: 'yAxis1',
          },
          {
            label: 'Water Level',
            data: XLD["WaterLevel"],
            yAxisID: 'yAxis2',
          }
        ]
      },
      options: {
        responsive: true,
        scales: {
          x: {
            type: 'linear',
            position: 'bottom',
            title: {
              display: true,
              text: 't(h)'
            },
            grid: {
              drawOnChartArea: false,
            },            
          },
          yAxis1: {
            type: 'linear',
            position: 'left',
            title: {
              display: true,
              text: '流量(m³/s)'
            },
            grid: {
              drawOnChartArea: false,
            },            
          },
          yAxis2: {
            type: 'linear',
            position: 'right',
            title: {
              display: true,
              text: '水位(m)'
            },
            grid: {
              drawOnChartArea: false,
            },            
          }
        }
      }
    });
  });
  
  // Fetch the JSON data for Sanmenxia
  fetch('Sanmenxia.json')
    .then(response => response.json())
    .then(data => {
      SMX = data;
      // Get the second chart area
      var ctx = document.getElementById('chartArea2').getContext('2d');

      // Create the chart
      chart2 = new Chart(ctx, {
        type: 'line',
        data: {
          labels: SMX.t,
          datasets: [
            {
              label: 'Inflow',
              data: SMX.Inflow,
              yAxisID: 'yAxisSMX1',
            },
            {
              label: 'Outflow',
              data: SMX.Outflow,
              yAxisID: 'yAxisSMX1',
            },
            {
              label: 'Water Level',
              data: SMX["WaterLevel"],
              yAxisID: 'yAxisSMX2',
            }
          ]
        },
        options: {
          responsive: true,
          scales: {
            x: {
              type: 'linear',
              position: 'bottom',
              title: {
                display: true,
                text: 't(h)'
              },
              grid: {
                drawOnChartArea: false,
              },
            },
            yAxisSMX1: {
              type: 'linear',
              position: 'left',
              title: {
                display: true,
                text: '流量(m³/s)'
              },
              grid: {
                drawOnChartArea: false,
              },
            },
            yAxisSMX2: {
              type: 'linear',
              position: 'right',
              title: {
                display: true,
                text: '水位(m)'
              },
              grid: {
                drawOnChartArea: false,
              },
            }
          }
        }
      });
    });

  //处理表格输入
  var tables = ['table1', 'table2'];

  for (var t = 0; t < tables.length; t++) {
    var table = document.getElementsByClassName(tables[t])[0];
    var inputs = table.getElementsByClassName('serial-number');
    var inputsT = table.getElementsByClassName('input-t');
    var inputsQ = table.getElementsByClassName('input-q');

    for (var i = 0; i < inputs.length; i++) {
      inputs[i].value = i + 1;
      (function(i, t) {
      inputsT[i].addEventListener('input', function () {
        if (tables[t] === 'table1') {
          XLD_t[i] = Number(this.value);
        } else {
          SMX_t[i] = Number(this.value);
        }
      });
      inputsQ[i].addEventListener('input', function () {
        if (isNaN(this.value)) {
          if (tables[t] === 'table1') {
            XLD_q[i] = NaN;
          } else {
            SMX_q[i] = NaN;
          }
        } else {
          if (tables[t] === 'table1') {
            XLD_q[i] = Number(this.value);
          } else {
            SMX_q[i] = Number(this.value);
          }
        }
      });
    })(i, t);
    }
    //console.log('t values for table ' + (t + 1) + ':', tables[t] === 'table1' ? XLD_t : SMX_t);
    //console.log('Q values for table ' + (t + 1) + ':', tables[t] === 'table1' ? XLD_q : SMX_q);
  }
  
  var table = document.getElementsByClassName('table1')[0];
  var inputsQ = table.getElementsByClassName('input-q');
  var inputsT = table.getElementsByClassName('input-t');
  var table = document.getElementsByClassName('table2')[0];
  var inputsQ_SMX = table.getElementsByClassName('input-q');
  var inputsT_SMX = table.getElementsByClassName('input-t');
  //令inputsT[0]的文本框边框颜色变为红色
  inputsT[0].style.borderColor = 'red';

  inputsT[0].addEventListener('blur', function () {
    if (this.value !== '') {
      inputsT_SMX[0].value = this.value;
      SMX_t[0] = Number(this.value);
      //令inputsT[0]的文本框边框颜色恢复默认
      inputsT[0].style.borderColor = '';
      //令inputsQ[0]的文本框边框颜色变为红色
      inputsQ[0].style.borderColor = 'red';
    }
  });
  //令table1的第二行的Q和第一行的Q相等，这两个单元格显示的值也相同
  inputsQ[0].addEventListener('blur', function () {
    if (this.value !== '') {
      inputsQ[1].value = this.value;
      XLD_q[1] = Number(this.value);
      inputsQ[0].style.borderColor = '';
      inputsT[1].style.borderColor = 'red';
    }
  });

  inputsQ[0].addEventListener('mouseover', function () {
    this.title = '下游不淤流量';
  });

  //table1的第二行的t输入后，第三和第四行的t自动计算
  inputsT[1].addEventListener('blur', function () {
    if (this.value !== '') {
      inputsT[2].value = Number(this.value) + 60;
      XLD_t[2] = Number(this.value) + 60;
    }
  });

  inputsT[1].addEventListener('blur', function () {
    if (this.value !== '') {
      inputsT[1].style.borderColor = '';
      inputsQ[2].style.borderColor = 'red';
    }
  });

  inputsQ[2].addEventListener('blur', function () {
    if (this.value !== '') {
      inputsQ[3].value = this.value;
      XLD_q[3] = Number(this.value);

      //计算现有水量
      var xx = XLD.CapCurve.WL;
      var yy = XLD.CapCurve.Vol;
      var x = XLD["WaterLevel"][0];
      var VolIni = interpolate(xx, yy, x);      //调用interpolate函数
      //读取id为WL-FloodControl的input的值
      WlFldContr_XLD = document.getElementById('WL-FloodControl').value;
      //如果是空值，提醒用户输入小浪底汛限水位
      if (WlFldContr_XLD === '') {
        alert('请输入小浪底汛限水位');
      } else {
        //计算对应的水量
        var Vol_FldContr = interpolate(xx, yy, WlFldContr_XLD);
        var netOutflowVol = VolIni - Vol_FldContr;     //净流出水量
        inputsT[3].value = CalculateT(netOutflowVol, XLD.t, XLD.Inflow, 3, 1, 1);
        XLD_t[3] = Number(inputsT[3].value);
      }
      inputsQ[2].style.borderColor = '';
      inputsQ[4].style.borderColor = 'red';
    }
  });


  inputsQ[4].addEventListener('blur', function () {
    if (this.value !== '') {
      WlReg_XLD = document.getElementById('WL-WaterSedReg').value;
      if (WlReg_XLD === '') {
        alert('请输入小浪底对接水位');
      } else {
        var xx = XLD.CapCurve.WL;
        var yy = XLD.CapCurve.Vol;
        var x = XLD["WaterLevel"][0];
        var VolIni = interpolate(xx, yy, x);      //调用interpolate函数                
        var Vol_StartReg = interpolate(xx, yy, WlReg_XLD);
        var netOutflowVol = VolIni - Vol_StartReg;     //净流出水量
        inputsT[4].value = CalculateT(netOutflowVol, XLD.t, XLD.Inflow, 4, 1, 2);
        XLD_t[4] = Number(inputsT[4].value);
      }
    }
    inputsQ[4].style.borderColor = '';
    inputsT_SMX[1].style.borderColor = 'red';
  });

  //鼠标悬停在inputsT[4]上时间，显示一个提示
  inputsT[4].addEventListener('mouseover', function () {
    this.title = '达到对接水位的时刻';
  });

  inputsQ[5].addEventListener('blur', function () { 
    if (this.value !== '') {
      inputsQ[6].value = this.value;
      XLD_q[6] = Number(this.value);

      inputsQ[5].style.borderColor = '';
      inputsT_SMX[3].style.borderColor = 'red';  
    }
  });

  inputsQ[9].addEventListener('blur', function () {
    if (this.value !== '') {
      inputsQ[10].value = this.value;
      XLD_q[9] = Number(this.value);
      XLD_q[10] = Number(this.value);
      
      inputsQ[9].style.borderColor = '';
      inputsT[10].style.borderColor = 'red';
    }
  });

  inputsT[10].addEventListener('blur', function () {
    if (this.value !== '') {
      volWatSupply = document.getElementById('Vol-WatSupply').value;
      if (volWatSupply === '') {
        alert('请输入小浪底期末可供水量');
      } else {
        xx = SMX.CapCurve.WL;
        yy = SMX.CapCurve.Vol;
        x = SMX["WaterLevel"][0];
        VolIni = interpolate(xx, yy, x);
        x = document.getElementById('WL-FloodControl-SMX').value;
        var Vol_FldContr_SMX = interpolate(xx, yy, x);
        netOutflowVol = VolIni - Vol_FldContr_SMX;
        inputsT_SMX[5].value = CalculateT(netOutflowVol, SMX.t, SMX.Inflow, 5, 2, 1);
        SMX_t[5] = Number(inputsT_SMX[5].value);
        inputsT_SMX[6].value = SMX_t[5];
        SMX_t[6] = Number(SMX_t[5]);  

      
        var xx = XLD.CapCurve.WL;
        var yy = XLD.CapCurve.Vol;
        var x = XLD["WaterLevel"][0];
        var VolIni = interpolate(xx, yy, x);
        var vol_210 = interpolate(xx, yy, 210);
        var netOutflowVol = VolIni - (vol_210 + Number(volWatSupply));
        inputsT[8].value = CalculateRefillT(netOutflowVol, SMX_t, SMX_q, SMX.t, SMX.Inflow, XLD_t, XLD_q);
        XLD_t[8] = Number(inputsT[8].value);
        inputsT[9].value = XLD_t[8];
        XLD_t[9] = XLD_t[8];

        inputsT[10].style.borderColor = '';
      }
    }
  });
  
  inputsT_SMX[1].addEventListener('blur', function () {
    if (this.value !== '') {
      inputsT_SMX[1].style.borderColor = '';
      inputsQ_SMX[2].style.borderColor = 'red';
    }
  });

  inputsQ_SMX[2].addEventListener('blur', function () {
    if (this.value !== '') {
      var xx = SMX.t;
      var yy = SMX.Inflow;
      var x = SMX_t[1];
      var q1 = interpolate(xx, yy, x);
      var q2 = this.value;
      var qIncrRate = 134.8;       //单位：m3/s/h
      inputsT_SMX[2].value = SMX_t[1] + (q2 - q1) / qIncrRate;
      if (q2 < q1) {
        alert('SMX_q[2]过小, 三门峡泄空冲刷流量小于入库流量');
      }
      SMX_t[2] = Number(inputsT_SMX[2].value);
      if (SMX_t[2] < XLD_t[4]) {
        alert('SMX_t[2] < XLD_t[4]');
      } else {
        inputsT[5].value = SMX_t[2];
        XLD_t[5] = SMX_t[2];;
        inputsQ_SMX[2].style.borderColor = '';
        inputsQ[5].style.borderColor = 'red';

        inputsQ_SMX[3].value = this.value;
        SMX_q[3] = Number(this.value);
      }
    }
  });

  inputsT_SMX[3].addEventListener('blur', function () {
    if (this.value !== '') {
      inputsT[6].value = this.value;
      XLD_t[6] = Number(this.value);

      inputsT[7].value = Number(this.value) + 24;
      XLD_t[7] = Number(this.value) + 24;

      inputsT_SMX[4].value = Number(this.value) + 24;
      SMX_t[4] = Number(this.value) + 24;
      inputsT_SMX[3].style.borderColor = '';
      inputsQ_SMX[4].style.borderColor = 'red';
    }
  });

  inputsQ_SMX[4].addEventListener('blur', function () {
    if (this.value !== '') {
      SMX_q[4] = Number(this.value);
      inputsQ[7].value = this.value;
      XLD_q[7] = Number(this.value);

      inputsQ_SMX[5].value = this.value;
      SMX_q[5] = Number(this.value);

      inputsQ[8].value = this.value;
      XLD_q[8] = Number(this.value);
      inputsQ_SMX[4].style.borderColor = '';
      inputsQ[9].style.borderColor = 'red';
    }
  });
}
    
//保存按钮
  document.getElementById('save').addEventListener('click', function () {
    var XLD_keypoints = {
      t: XLD_t,
      q: XLD_q,
      WlFldContr: Number(WlFldContr_XLD),
      WlReg: Number(WlReg_XLD),
      volWatSupply: Number(volWatSupply)
    };
    var SMX_keypoints = {
      t: SMX_t,
      q: SMX_q,
      WlFldContr: Number(document.getElementById('WL-FloodControl-SMX').value)
    };

    saveToFile(XLD_keypoints, 'XLD_keypoints.json');
    saveToFile(SMX_keypoints, 'SMX_keypoints.json');
  });

  function saveToFile(data, filename) {
    var blob = new Blob([JSON.stringify(data)], { type: 'application/json' });
    var url = URL.createObjectURL(blob);
    var a = document.createElement('a');
    a.href = url;
    a.download = filename;
    a.click();
  }

//绘制调控过程线
document.getElementById('plot').addEventListener('click', function () {
  // 创建XLD调控过程线数据，过滤掉NaN值
  let XLD_RegCurve = {
    label: 'Regulated Discharge',
    data: XLD_t.map((t, i) => {
      if (!isNaN(XLD_q[i])) {
        return { x: t, y: XLD_q[i] };
      }
      return null;
    }).filter(point => point !== null),
    yAxisID: 'yAxis1',
    borderColor: '#006400', // 深绿色
    backgroundColor: '#006400'
  };

  chart1.data.datasets.push(XLD_RegCurve);
  chart1.update();

  // 创建SMX调控过程线数据，过滤掉NaN值
  let SMX_RegCurve = {
    label: 'Regulated Discharge',
    data: SMX_t.slice(2, 6).map((t, i) => {
      if (!isNaN(SMX_q[i + 2])) {
        return { x: t, y: SMX_q[i + 2] };
      }
      return null;
    }).filter(point => point !== null),
    yAxisID: 'yAxisSMX1',
    borderColor: '#006400', // 深绿色
    backgroundColor: '#006400'
  };

  chart2.data.datasets.push(SMX_RegCurve);
  chart2.update();
});

//生成初始方案
document.getElementById('GenerateInitialPlan').addEventListener('click', function () {
    if (typeof GenerateIniP === 'function') {
        GenerateIniP();
    } else {
        console.error('GenerateIniP function is not defined');
    }
});