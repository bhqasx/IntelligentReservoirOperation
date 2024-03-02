var XLD_t = [], XLD_q = [], SMX_t = [], SMX_q = [];
var XLD = {};
var SMX = {};

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
  var i = 0;
  while (xx[i] < x) {
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
    } else {
        var t1 = SMX_t[iLastKeyP - 1];
    }
  return t2;
}

window.onload = function() {
// Fetch the JSON data for Xiaolangdi
fetch('Xiaolangdi.json')
  .then(response => response.json())
  .then(data => {
    XLD = data;
    // Get the first chart area
    var ctx = document.getElementById('chartArea1').getContext('2d');

    // Create the chart
    new Chart(ctx, {
      type: 'line',
      data: {
        labels: XLD.t,
        datasets: [
          {
            label: 'Inflow',
            data: XLD.Inflow,
            yAxisID: 'y-axis-1',
          },
          {
            label: 'Outflow',
            data: XLD.Outflow,
            yAxisID: 'y-axis-1',
          },
          {
            label: 'Water Level',
            data: XLD["Water level"],
            yAxisID: 'y-axis-2',
          }
        ]
      },
      options: {
        responsive: true,
        scales: {
          yAxes: [
            {
              id: 'y-axis-1',
              type: 'linear',
              position: 'left',
            },
            {
              id: 'y-axis-2',
              type: 'linear',
              position: 'right',
            }
          ]
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
      new Chart(ctx, {
        type: 'line',
        data: {
          labels: SMX.t,
          datasets: [
            {
              label: 'Inflow',
              data: SMX.Inflow,
              yAxisID: 'y-axis-1',
            },
            {
              label: 'Outflow',
              data: SMX.Outflow,
              yAxisID: 'y-axis-1',
            },
            {
              label: 'Water Level',
              data: SMX["Water level"],
              yAxisID: 'y-axis-2',
            }
          ]
        },
        options: {
          responsive: true,
          scales: {
            yAxes: [
              {
                id: 'y-axis-1',
                type: 'linear',
                position: 'left',
              },
              {
                id: 'y-axis-2',
                type: 'linear',
                position: 'right',
              }
            ]
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
            var x = XLD["Water level"][0];
            var VolIni = interpolate(xx, yy, x);      //调用interpolate函数
            //读取id为WL-FloodControl的input的值
            var WlFldContr_XLD = document.getElementById('WL-FloodControl').value;
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

    //鼠标悬停在inputsQ[4]上时间，显示一个提示
    inputsQ[4].addEventListener('mouseover', function () {
        this.title = '下游不淤流量';
    });
    inputsQ[4].addEventListener('blur', function () {
        if (this.value !== '') {
            var WlReg_XLD = document.getElementById('WL-WaterSedReg').value;
            if (WlReg_XLD === '') {
                alert('请输入小浪底对接水位');
            } else {
                var xx = XLD.CapCurve.WL;
                var yy = XLD.CapCurve.Vol;
                var x = XLD["Water level"][0];
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

    //table1的第二行的t输入后，第三和第四行的t自动计算
    inputsT[1].addEventListener('blur', function () {
        if (this.value !== '') {
            inputsT[2].value = Number(this.value) + 60;
            XLD_t[2] = Number(this.value) + 60;
        }
    });
}
    
//保存按钮
  document.getElementById('save').addEventListener('click', function () {
    var XLD_keypoints = {
      t: XLD_t,
      q: XLD_q
    };
    var SMX_keypoints = {
      t: SMX_t,
      q: SMX_q
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