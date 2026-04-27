

% SetFlowRate(app.LI,'Pump_pH',100,'Pump_Na',100,'Pump_K',100,'Pump_aCSF',100,'Pump_Ca',100)
% MulMove2(app.LI,'Pump_pH',10,'Pump_aCSF',10,'Pump_K',10,'Pump_Na',10,'Pump_Ca',10)
% MulMove2(app.LI,'Pump_pH',1,'Pump_aCSF',1,'Pump_K',1,'Pump_Na',1,'Pump_Ca',1)
% a=1;
% SetValves(app.LI,'Manifold1',a,a,a,a)
% SetValves(app.LI,'Manifold2',a,a,a,a)
% a=3;
% SetValves(app.LI,'Manifold1',a,a,a,a)
% SetValves(app.LI,'Manifold2',a,a,a,a)

% a=3;
% SetValves(app.LI,'Manifold1',a,a,a,a,'Manifold2',a,a,a,a)
% a=1;
% SetValves(app.LI,'Manifold1',a,a,a,a,'Manifold2',a,a,a,a)
% 
% SetFlowRate(app.LI,'Pump_pH',100,'Pump_Na',5,'Pump_K',100,'Pump_aCSF',5,'Pump_Ca',100)
% % MoveWait(app.LI,5,'Pump_pH',1,'Pump_K',1,'Pump_Na',1,'Pump_aCSF',1);
% MulMove3(app.LI,'Pump_pH',5)
% 
% a=3;
% SetValves(app.LI,'Manifold1',a,a,a,a,'Manifold2',a,a,a,a)
% 
% MulMove3(app.LI,'Pump_pH',1)

% a=10;
% MulMove3(app.LI,'Pump_K',a,'Pump_pH',a,'Pump_aCSF',a,'Pump_Na',a)
% MulMove3(app.LI,'Pump_K',3,'Pump_pH',6,'Pump_aCSF',9,'Pump_Na',12,'Pump_Ca',15)
% MulMove3(app.LI,'Pump_K',10,'Pump_pH',10)


a=3;
SetValves2(app.LI,'Manifold1',a,a,a,a)
MulMove3(app.LI,'Pump_pH',8)
a=1;
SetValves2(app.LI,'Manifold1',a,a,a,a)
MulMove3(app.LI,'Pump_pH',1)
% a=3;
% SetValves2(app.LI,'Manifold1',a,a,a,a)
% MulMove3(app.LI,'Pump_pH',3)
% a=1;
% SetValves2(app.LI,'Manifold1',a,a,a,a)
% MulMove3(app.LI,'Pump_pH',1)