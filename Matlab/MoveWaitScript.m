
SetFlowRate(app.LI,'Pump_pH',100,'Pump_Na',5,'Pump_K',100,'Pump_aCSF',5,'Pump_Ca',100)
MoveWait(app.LI,5,'Pump_pH',1,'Pump_K',1,'Pump_Na',1,'Pump_aCSF',1);
% MoveWait(app.LI,3,'Pump_pH',10);
