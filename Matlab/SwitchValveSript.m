% for i=1:10
%     comment=['iteration ',num2str(i)];
%     disp(comment)
%     a=3;
%     SetValves2(app.LI,'Manifold1',a,a,a,a,'Manifold2',a,a,a,a)
%     a=2;
%     SetValves2(app.LI,'Manifold1',a,a,a,a,'Manifold2',a,a,a,a)
%     a=1;
%     SetValves2(app.LI,'Manifold1',a,a,a,a,'Manifold2',a,a,a,a)
%     a=2;
%     SetValves2(app.LI,'Manifold1',a,a,a,a,'Manifold2',a,a,a,a)    
% end

a=3;
SetValves2(app.LI,'Manifold1',a,a,a,a,'Manifold2',a,a,a,a)
a=1;
SetValves2(app.LI,'Manifold1',a,a,a,a,'Manifold2',a,a,a,a)