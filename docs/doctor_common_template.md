# 医生通用模板

以下模板是根据仓库里现有 `doctor_*` 项目的字段交集，以及当前医生主表字段需求整理的，适合做统一入库口径。

## 核心字段

```json
{
  "_id": "",
  "doctor_id": "",
  "doctor_name": "",
  "doctor_hospital": "",
  "doctor_department": "",
  "doctor_title": "",
  "doctor_avatar_url": "",
  "doctor_specialties": "",
  "intro": "",
  "source_site": "",
  "source_url": "",
  "crawl_time": ""
}
```

## 通用含义

- `_id`：Mongo 主键
- `doctor_id`：医生唯一 ID
- `doctor_name`：医生姓名
- `doctor_hospital`：医院名
- `doctor_department`：科室名
- `doctor_title`：职称
- `doctor_avatar_url`：头像地址
- `doctor_specialties`：擅长/诊疗项目
- `intro`：简介正文
- `source_site`：来源站点
- `source_url`：来源链接
- `crawl_time`：采集日期

## 医生补充字段

下面这组字段作为“按需触发”的补充字段：

- 页面里遇到就采
- 页面里没有就不写空字段
- 命名统一使用 `doctor_*` 风格

```json
{
  "doctor_province": "",
  "doctor_city": "",
  "doctor_county": "",
  "doctor_prof_title": "",
  "doctor_hospital_grade": "",
  "doctor_hospital_nature": "",
  "doctor_hospital_property": "",
  "doctor_first_category": "",
  "doctor_second_category": "",
  "doctor_first_department_std_id": "",
  "doctor_first_department_std_name": "",
  "doctor_second_department_std_id": "",
  "doctor_second_department_std_name": "",
  "doctor_prof_direction": "",
  "doctor_graduated": "",
  "doctor_edu_process": "",
  "doctor_work_process": "",
  "doctor_social_activity": "",
  "doctor_summary": "",
  "doctor_expertise": "",
  "doctor_summary_words": "",
  "doctor_social_job": "",
  "doctor_research_direction": "",
  "doctor_published_works": "",
  "doctor_achievements": "",
  "doctor_person_honor": "",
  "doctor_motto": "",
  "doctor_work_value": "",
  "doctor_clinical_record": "",
  "doctor_exp_analysis": "",
  "doctor_exp_technology": "",
  "doctor_is_attended": "",
  "doctor_has_feedback": "",
  "doctor_longitude": "",
  "doctor_latitude": "",
  "doctor_hospital_id_backup": "",
  "doctor_title_backups": "",
  "doctor_avatar_backup": "",
  "doctor_avatar_removebg_before": "",
  "doctor_third_party_id": ""
}
```

## 医生补充字段含义

- `doctor_prof_title`：学术 / 教学职称
- `doctor_prof_direction`：专业方向
- `doctor_graduated`：毕业院校
- `doctor_edu_process`：教育经历
- `doctor_work_process`：工作经历
- `doctor_social_activity`：社会活动
- `doctor_summary`：擅长领域 / 诊治范围汇总
- `doctor_expertise`：主要擅长
- `doctor_summary_words`：从擅长字段中提取出的疾病、治疗手段等关键词
- `doctor_social_job`：学术兼职
- `doctor_research_direction`：研究方向
- `doctor_published_works`：出版著作
- `doctor_achievements`：科研成果
- `doctor_person_honor`：荣誉与奖项

## 不纳入采集模板的字段

下面这类字段默认不放进采集模板：

- 自增主键
- 排序权重字段
- 校验状态字段
- 白名单状态字段
- 删除状态字段
- `created_time`
- `updated_time`
- 拼音冗余字段
- 明显只用于后台内部管理的布尔/排序字段

## 医院通用字段

如果项目里需要同时沉淀医院集合，建议统一使用下面这套 `hospital_*` 风格字段：

```json
{
  "_id": "",
  "hospital_id": "",
  "hospital_name": "",
  "hospital_address": "",
  "hospital_phone": "",
  "hospital_intro": "",
  "hospital_level": "",
  "hospital_nature": "",
  "hospital_type": "",
  "hospital_property": "",
  "hospital_website": "",
  "hospital_insurance": "",
  "hospital_offices": "",
  "hospital_special": "",
  "hospital_advantage": "",
  "source_site": "",
  "source_url": "",
  "crawl_time": ""
}
```

## 医院字段含义

- `_id`：Mongo 主键，统一等于 `hospital_id`
- `hospital_id`：来源站点医院 ID
- `hospital_name`：医院名称
- `hospital_address`：医院地址
- `hospital_phone`：联系电话
- `hospital_intro`：医院简介
- `hospital_level`：医院等级原始值
- `hospital_nature`：医院性质
- `hospital_type`：医院类型
- `hospital_property`：医院属性
- `hospital_website`：医院官网
- `hospital_insurance`：是否医保定点
- `hospital_offices`：科室设置
- `hospital_special`：特色专科
- `hospital_advantage`：医疗优势
- `source_site`：来源站点
- `source_url`：来源链接
- `crawl_time`：采集日期

## 建议口径

- 核心字段尽量固定，不要随站点改名
- 扩展字段可以有，但不要影响核心模板
- 医生补充字段采用“遇到则写，没有则不写空字段”的策略
- 医院字段统一使用 `hospital_*` 风格，不建议混用 `name` / `address` / `intro` 这类裸字段
- 如果某站点没有 `doctor_department`，可以先留空
- 如果某站点只有简介和姓名，也至少保留核心字段和来源字段
