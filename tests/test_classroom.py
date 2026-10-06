import pytest

from materia import classroom, store


def test_course_assignment_and_submission_flow(tmp_path, monkeypatch):
    monkeypatch.setattr(store,'DB',tmp_path/'classroom.sqlite3')
    course=classroom.create_course('teacher-1','Polymères M1','Cours de vieillissement',authorized_teacher=True)
    assert course['role']=='teacher'
    joined=classroom.join_course('student-1',course['code'],'Alice Exemple')
    assert joined['role']=='student'
    assignment=classroom.create_assignment('teacher-1',course['id'],'Étude PP',
        'Comparer le seuil à 80 % et commenter les limites.','estimation','2026-10-15')
    simulation_id=store.save('student-1','simulation','PP extérieur',{'fingerprint':'abc','retention':[100,90]})
    result=classroom.submit('student-1',assignment['id'],simulation_id,'Alice Exemple','Résultat commenté.')
    assert result['status']=='submitted'
    submissions=classroom.submissions('teacher-1',course['id'])
    assert len(submissions)==1
    assert submissions[0]['assignment_title']=='Étude PP'
    assert submissions[0]['simulation_name']=='PP extérieur'
    reviewed=classroom.review_submission('teacher-1',submissions[0]['id'],16.5,'Analyse correcte, limites à préciser.')
    assert reviewed['grade']==16.5
    stats=classroom.course_stats('teacher-1',course['id'])
    assert stats=={'students':1,'assignments':1,'submissions':1,'reviewed':1,
                   'pending_review':0,'average_grade':16.5}
    copy=classroom.duplicate_assignment('teacher-1',assignment['id'],'2026-11-15')
    assert copy['title']=='Copie de Étude PP'
    assert copy['due_date']=='2026-11-15'
    assert classroom.course_stats('teacher-1',course['id'])['assignments']==2
    student_view=classroom.student_submissions('student-1',course['id'])
    assert student_view[0]['status']=='reviewed'
    assert student_view[0]['feedback'].startswith('Analyse correcte')


def test_classroom_permissions(tmp_path, monkeypatch):
    monkeypatch.setattr(store,'DB',tmp_path/'permissions.sqlite3')
    with pytest.raises(PermissionError):
        classroom.create_course('student','Cours interdit')
    course=classroom.create_course('teacher','Cours test',authorized_teacher=True)
    with pytest.raises(PermissionError):
        classroom.create_assignment('student',course['id'],'Travail test','Une consigne suffisamment longue.','guided')
    with pytest.raises(PermissionError):
        classroom.submissions('student',course['id'])
    with pytest.raises(PermissionError):
        classroom.review_submission('student','unknown',15,'Retour interdit')
    with pytest.raises(ValueError):
        classroom.join_course('student','BADCODE','Alice')
    with pytest.raises(PermissionError):
        classroom.course_stats('student',course['id'])
    assignment=classroom.create_assignment('teacher',course['id'],'Travail test','Une consigne suffisamment longue.','guided')
    with pytest.raises(PermissionError):
        classroom.duplicate_assignment('student',assignment['id'])
    with pytest.raises(ValueError,match='AAAA-MM-JJ'):
        classroom.create_assignment('teacher',course['id'],'Date invalide','Une consigne suffisamment longue.','guided','31/12/2026')


def test_guest_classroom_transfer_respects_role(tmp_path, monkeypatch):
    monkeypatch.setattr(store,'DB',tmp_path/'transfer-classroom.sqlite3')
    course=classroom.create_course('guest-teacher','Cours invité',authorized_teacher=True)
    classroom.join_course('guest-student',course['code'],'Alice')
    simulation=store.save('guest-student','simulation','Résultat',{'value':1})
    assignment=classroom.create_assignment('guest-teacher',course['id'],'Analyse PP','Interpréter les limites du résultat.','estimation')
    classroom.submit('guest-student',assignment['id'],simulation,'Alice')
    assert classroom.transfer_owner('guest-student','student-account')==2
    assert classroom.courses_for_owner('student-account')[0]['role']=='student'
    assert classroom.student_submissions('student-account',course['id'])[0]['simulation_name']=='Résultat'
    assert classroom.transfer_owner('guest-teacher','teacher-account',include_teacher_content=True)==2
    assert classroom.courses_for_owner('teacher-account')[0]['role']=='teacher'
