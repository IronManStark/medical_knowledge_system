CREATE DATABASE IF NOT EXISTS `mks` DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

USE `mks`;

DROP TABLE IF EXISTS `knowledge_entry`;
DROP TABLE IF EXISTS `knowledge_template`;
DROP TABLE IF EXISTS `model_config`;
DROP TABLE IF EXISTS `access_log`;
DROP TABLE IF EXISTS `system_setting`;
DROP TABLE IF EXISTS `category`;
DROP TABLE IF EXISTS `user`;
DROP TABLE IF EXISTS `role`;
DROP TABLE IF EXISTS `department`;

CREATE TABLE `department` (
    `id` INT AUTO_INCREMENT PRIMARY KEY COMMENT '科室ID',
    `name` VARCHAR(80) NOT NULL COMMENT '科室名称',
    `code` VARCHAR(30) UNIQUE NOT NULL COMMENT '科室编码',
    `parent_id` INT NULL COMMENT '上级科室',
    `sort_order` INT DEFAULT 0 COMMENT '排列序号',
    `remark` VARCHAR(200) DEFAULT '' COMMENT '备注',
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    INDEX `idx_parent_id` (`parent_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='科室信息表';

CREATE TABLE `role` (
    `id` INT AUTO_INCREMENT PRIMARY KEY COMMENT '角色ID',
    `name` VARCHAR(50) UNIQUE NOT NULL COMMENT '角色名称',
    `code` VARCHAR(30) UNIQUE NOT NULL COMMENT '角色编码',
    `permissions` TEXT COMMENT '权限列表，逗号分隔',
    `remark` VARCHAR(200) DEFAULT '' COMMENT '备注',
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='角色与权限定义表';

CREATE TABLE `user` (
    `id` INT AUTO_INCREMENT PRIMARY KEY COMMENT '用户ID',
    `username` VARCHAR(50) UNIQUE NOT NULL COMMENT '登录账号',
    `real_name` VARCHAR(50) NOT NULL COMMENT '真实姓名',
    `password_hash` VARCHAR(128) NOT NULL COMMENT '口令哈希',
    `email` VARCHAR(120) DEFAULT '' COMMENT '电子邮箱',
    `phone` VARCHAR(20) DEFAULT '' COMMENT '联系电话',
    `department_id` INT NULL COMMENT '所属科室',
    `role_id` INT NULL COMMENT '所属角色',
    `status` VARCHAR(10) DEFAULT 'active' COMMENT '账号状态 active/disabled',
    `failed_attempts` INT DEFAULT 0 COMMENT '密码错误次数',
    `lock_time` DATETIME NULL COMMENT '账号锁定时间',
    `last_login` DATETIME NULL COMMENT '最后登录时间',
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    INDEX `idx_department_id` (`department_id`),
    INDEX `idx_role_id` (`role_id`),
    INDEX `idx_username` (`username`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='系统用户表';

CREATE TABLE `category` (
    `id` INT AUTO_INCREMENT PRIMARY KEY COMMENT '分类ID',
    `name` VARCHAR(80) NOT NULL COMMENT '分类名称',
    `code` VARCHAR(30) UNIQUE NOT NULL COMMENT '分类编码',
    `parent_id` INT NULL COMMENT '上级分类',
    `level` INT DEFAULT 1 COMMENT '层级',
    `sort_order` INT DEFAULT 0 COMMENT '排列序号',
    `description` VARCHAR(300) DEFAULT '' COMMENT '分类描述',
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    INDEX `idx_parent_id` (`parent_id`),
    INDEX `idx_sort_order` (`sort_order`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='知识分类体系表';

CREATE TABLE `knowledge_entry` (
    `id` INT AUTO_INCREMENT PRIMARY KEY COMMENT '知识条目ID',
    `title` VARCHAR(200) NOT NULL COMMENT '知识标题',
    `category_id` INT NULL COMMENT '所属分类',
    `summary` TEXT COMMENT '摘要',
    `definition` TEXT COMMENT '定义',
    `etiology` TEXT COMMENT '病因',
    `clinical_manifestation` TEXT COMMENT '临床表现',
    `diagnosis` TEXT COMMENT '诊断标准',
    `treatment` TEXT COMMENT '治疗方案',
    `prevention` TEXT COMMENT '预防措施',
    `references` TEXT COMMENT '参考文献',
    `tags` VARCHAR(300) DEFAULT '' COMMENT '标签，逗号分隔',
    `source` VARCHAR(20) DEFAULT 'manual' COMMENT '来源 manual/generated',
    `status` VARCHAR(20) DEFAULT 'draft' COMMENT '状态 draft/pending/published/rejected',
    `version` INT DEFAULT 1 COMMENT '版本号',
    `created_by` INT NULL COMMENT '创建人',
    `reviewed_by` INT NULL COMMENT '审核人',
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    `reviewed_at` DATETIME NULL COMMENT '审核时间',
    INDEX `idx_category_id` (`category_id`),
    INDEX `idx_created_by` (`created_by`),
    INDEX `idx_status` (`status`),
    INDEX `idx_title` (`title`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='医学知识条目主表';

CREATE TABLE `knowledge_template` (
    `id` INT AUTO_INCREMENT PRIMARY KEY COMMENT '模板ID',
    `name` VARCHAR(80) NOT NULL COMMENT '模板名称',
    `field_definitions` TEXT NOT NULL COMMENT 'JSON格式字段定义',
    `is_default` TINYINT(1) DEFAULT 0 COMMENT '是否默认模板',
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='知识录入模板表';

CREATE TABLE `model_config` (
    `id` INT AUTO_INCREMENT PRIMARY KEY COMMENT '配置ID',
    `name` VARCHAR(80) NOT NULL COMMENT '配置名称',
    `api_url` VARCHAR(500) NOT NULL COMMENT '接口地址',
    `api_key` VARCHAR(300) DEFAULT '' COMMENT '密钥',
    `model_name` VARCHAR(100) NOT NULL COMMENT '模型名称',
    `temperature` FLOAT DEFAULT 0.3 COMMENT '生成温度',
    `max_tokens` INT DEFAULT 2048 COMMENT '最大返回token',
    `si_kao_mo_shi` TINYINT(1) DEFAULT 0 COMMENT '是否开启思考模式',
    `ti_shi_ci` TEXT COMMENT '生成提示词模板，{title}替换为知识名称，留空用系统内置模板',
    `is_active` TINYINT(1) DEFAULT 0 COMMENT '当前是否启用',
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    INDEX `idx_is_active` (`is_active`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='模型接口配置表';

CREATE TABLE `access_log` (
    `id` INT AUTO_INCREMENT PRIMARY KEY COMMENT '日志ID',
    `user_id` INT NULL COMMENT '操作人ID',
    `username` VARCHAR(50) DEFAULT '' COMMENT '操作人账号',
    `action` VARCHAR(50) NOT NULL COMMENT '操作类型',
    `module` VARCHAR(50) DEFAULT '' COMMENT '功能模块',
    `target` VARCHAR(200) DEFAULT '' COMMENT '操作对象',
    `ip_address` VARCHAR(50) DEFAULT '' COMMENT 'IP地址',
    `detail` TEXT COMMENT '详情',
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '操作时间',
    INDEX `idx_user_id` (`user_id`),
    INDEX `idx_created_at` (`created_at`),
    INDEX `idx_module` (`module`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='用户访问操作日志表';

CREATE TABLE `system_setting` (
    `id` INT AUTO_INCREMENT PRIMARY KEY COMMENT '设置ID',
    `key` VARCHAR(80) UNIQUE NOT NULL COMMENT '设置键',
    `value` TEXT COMMENT '设置值',
    `description` VARCHAR(200) DEFAULT '' COMMENT '设置描述',
    `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    INDEX `idx_key` (`key`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='系统参数键值对存储';

INSERT INTO `role` (`name`, `code`, `permissions`, `remark`) VALUES
('系统管理员', 'admin', 'user_manage,dept_manage,role_manage,knowledge_create,knowledge_edit,knowledge_review,knowledge_generate,category_manage,log_view,stat_view,model_config', '拥有全部权限'),
('知识编辑', 'editor', 'knowledge_create,knowledge_edit,knowledge_generate,category_manage', '知识录入和编辑'),
('审核员', 'reviewer', 'knowledge_review,log_view,stat_view', '知识审核和查看');

INSERT INTO `department` (`name`, `code`, `parent_id`, `sort_order`, `remark`) VALUES
('医务部', 'MED', NULL, 1, '医院行政管理部门'),
('内科', 'INT', NULL, 2, '内科科室'),
('外科', 'SUR', NULL, 3, '外科科室'),
('急诊科', 'EME', NULL, 4, '急诊科室'),
('药剂科', 'PHAR', NULL, 5, '药房科室');

INSERT INTO `user` (`username`, `real_name`, `password_hash`, `email`, `phone`, `department_id`, `role_id`, `status`) VALUES
('admin', '系统管理员', '$2b$12$xbvpNHX7ggfF.4DumcABGO8hZNeN0fwSwPaOgYlW8UbvCvTxZdCqm', 'admin@example.com', '13800138000', 1, 1, 'active');

INSERT INTO `category` (`name`, `code`, `parent_id`, `level`, `sort_order`, `description`) VALUES
('疾病', 'DISEASE', NULL, 1, 1, '疾病相关知识'),
('药品', 'MEDICINE', NULL, 1, 2, '药品相关知识'),
('检查', 'EXAM', NULL, 1, 3, '检查相关知识'),
('检验', 'LAB', NULL, 1, 4, '检验相关知识'),
('手术', 'SURGERY', NULL, 1, 5, '手术相关知识'),
('麻醉', 'ANESTHESIA', NULL, 1, 6, '麻醉相关知识'),
('健康宣教', 'HEALTH_EDU', NULL, 1, 7, '健康宣教知识');

INSERT INTO `knowledge_entry` (`title`, `category_id`, `summary`, `definition`, `etiology`, `clinical_manifestation`, `diagnosis`, `treatment`, `prevention`, `references`, `tags`, `source`, `status`, `version`, `created_by`) VALUES
('高血压', 1, '高血压是一种常见的慢性疾病，指血液在血管中流动时对血管壁造成的压力持续高于正常水平。', '高血压是指在未使用降压药物的情况下，收缩压≥140mmHg和（或）舒张压≥90mmHg。', '遗传因素、年龄增长、肥胖、缺乏运动、高盐饮食、长期精神紧张等多种因素共同作用。', '多数患者无症状，部分可出现头痛、头晕、心悸、耳鸣、视力模糊等症状。长期可导致心脑血管并发症。', '非同日三次测量血压，收缩压≥140mmHg和（或）舒张压≥90mmHg即可诊断。需排除继发性高血压。', '生活方式干预：低盐饮食、规律运动、戒烟限酒、控制体重；药物治疗：利尿剂、钙通道阻滞剂、ACEI、ARB等。', '定期体检、保持健康生活方式、控制危险因素、早期发现并治疗。', '《中国高血压防治指南2023》', '心血管,慢性病,血压', 'manual', 'published', 1, 1),
('糖尿病', 1, '糖尿病是一组以高血糖为特征的代谢性疾病，由胰岛素分泌缺陷或作用障碍引起。', '糖尿病是由于胰岛素分泌不足或胰岛素抵抗导致血糖水平持续升高的慢性疾病。', '遗传因素、环境因素（肥胖、缺乏运动、不良饮食）、自身免疫等。', '典型症状为多饮、多食、多尿、体重减轻。长期可导致眼、肾、神经、心血管等并发症。', '空腹血糖≥7.0mmol/L，或餐后2小时血糖≥11.1mmol/L，或随机血糖≥11.1mmol/L伴糖尿病症状。', '饮食控制、运动疗法、血糖监测、药物治疗（口服降糖药、胰岛素）。', '控制体重、规律运动、健康饮食、定期血糖筛查。', '《中国2型糖尿病防治指南2022年版》', '内分泌,代谢病,血糖', 'manual', 'published', 1, 1),
('冠心病', 1, '冠状动脉粥样硬化性心脏病，是由于冠状动脉粥样硬化导致血管狭窄或阻塞引起的心脏病。', '冠心病是指冠状动脉粥样硬化使血管腔狭窄或阻塞，导致心肌缺血缺氧或坏死的心脏病。', '高血脂、高血压、糖尿病、吸烟、肥胖、缺乏运动、家族史等。', '心绞痛：胸骨后压榨性疼痛，可放射至左肩、手臂、颈部；心肌梗死：剧烈而持久的胸痛，伴大汗、呼吸困难。', '心电图、心脏超声、冠状动脉CTA、冠状动脉造影等检查。', '药物治疗：抗血小板、他汀类、硝酸酯类；介入治疗：支架植入；手术治疗：冠状动脉旁路移植。', '控制危险因素、健康生活方式、定期体检。', '《中国冠心病防治指南》', '心血管,心脏病,动脉粥样硬化', 'manual', 'published', 1, 1),
('肺炎', 1, '肺炎是由细菌、病毒等病原体引起的肺部炎症，是常见的呼吸系统感染性疾病。', '肺炎是指终末气道、肺泡和肺间质的炎症，可由病原微生物、理化因素、免疫损伤等引起。', '细菌感染（肺炎链球菌、金黄色葡萄球菌）、病毒感染（流感病毒、冠状病毒）、真菌感染等。', '发热、咳嗽、咳痰、胸痛、呼吸困难等。', '临床表现结合血常规、胸片或CT、病原学检查。', '抗感染治疗（根据病原体选择抗生素或抗病毒药物）、对症支持治疗（退热、止咳、氧疗）。', '接种疫苗、保持呼吸道卫生、增强免疫力。', '《社区获得性肺炎诊断和治疗指南》', '呼吸,感染,肺部', 'manual', 'published', 1, 1),
('脑卒中', 1, '脑卒中又称中风，是急性脑血管疾病，包括缺血性脑卒中和出血性脑卒中。', '脑卒中是指因脑血管阻塞或破裂导致脑组织损伤的一组疾病。', '缺血性：动脉粥样硬化、血栓形成、栓塞；出血性：高血压、动脉瘤、血管畸形。', '突发肢体无力、言语不清、视物模糊、头晕、剧烈头痛等。', 'CT或MRI检查明确病变类型和部位。', '缺血性：溶栓治疗、抗血小板、改善脑循环；出血性：控制血压、降低颅内压、必要时手术。', '控制高血压、糖尿病、高血脂，戒烟限酒，定期体检。', '《中国急性缺血性脑卒中诊治指南2023》', '神经,脑血管,中风', 'manual', 'published', 1, 1),
('阿司匹林', 2, '阿司匹林是一种非甾体抗炎药，具有解热、镇痛、抗炎和抗血小板作用。', '阿司匹林是水杨酸类药物，通过抑制前列腺素合成发挥药理作用。', '', '', '', '解热镇痛：用于发热、头痛、关节痛等；抗血小板：用于预防心脑血管疾病。', '小剂量阿司匹林可用于预防心肌梗死、脑梗死等血栓性疾病。', '《中华人民共和国药典》', '解热镇痛,抗血小板,NSAIDs', 'manual', 'published', 1, 1),
('阿莫西林', 2, '阿莫西林是一种广谱半合成青霉素类抗生素，对多种细菌有杀菌作用。', '阿莫西林是口服青霉素类抗生素，通过抑制细菌细胞壁合成发挥杀菌作用。', '', '', '', '用于治疗敏感细菌引起的感染，如呼吸道感染、泌尿系统感染、皮肤软组织感染等。', '', '《抗菌药物临床应用指导原则》', '抗生素,青霉素,抗感染', 'manual', 'published', 1, 1),
('胰岛素', 2, '胰岛素是调节血糖的关键激素，用于治疗糖尿病。', '胰岛素是胰腺分泌的激素，促进葡萄糖摄取和利用，降低血糖水平。', '', '', '', '用于1型糖尿病和部分2型糖尿病的治疗，控制血糖水平。', '', '《中国2型糖尿病防治指南》', '激素,降糖药,糖尿病', 'manual', 'published', 1, 1),
('硝苯地平', 2, '硝苯地平是一种钙通道阻滞剂，用于治疗高血压和心绞痛。', '硝苯地平通过阻止钙离子进入血管平滑肌细胞，扩张血管降低血压。', '', '', '', '用于治疗高血压、心绞痛、冠心病等。', '', '《中国高血压防治指南》', '降压药,钙通道阻滞剂,心血管', 'manual', 'published', 1, 1),
('布洛芬', 2, '布洛芬是一种非甾体抗炎药，具有解热、镇痛和抗炎作用。', '布洛芬通过抑制前列腺素合成，发挥解热镇痛抗炎作用。', '', '', '', '用于缓解轻至中度疼痛，如头痛、关节痛、牙痛等；用于发热的退热治疗。', '', '《中华人民共和国药典》', '解热镇痛,NSAIDs,抗炎', 'manual', 'published', 1, 1),
('心电图', 3, '心电图是记录心脏电活动的检查方法，用于诊断心律失常、心肌缺血等心脏疾病。', '心电图是通过体表电极记录心脏在每个心动周期产生的电活动变化的图形。', '', '', '用于诊断心律失常、心肌缺血、心肌梗死、心脏扩大等。', '', '', '《临床心电图学》', '心脏检查,电生理,无创', 'manual', 'published', 1, 1),
('胸部CT', 3, '胸部CT是利用X射线对胸部进行断层扫描的检查方法，用于诊断肺部疾病。', '胸部CT是通过计算机断层扫描技术，对胸部进行多层、多角度成像的检查方法。', '', '', '用于诊断肺炎、肺结核、肺癌、胸腔积液、纵隔病变等。', '', '', '《医学影像学》', '影像学,肺部检查,CT', 'manual', 'published', 1, 1),
('超声心动图', 3, '超声心动图是利用超声波检查心脏结构和功能的无创检查方法。', '超声心动图是通过超声波反射成像，显示心脏各腔室、瓣膜、血管的结构和功能。', '', '', '用于评估心脏大小、室壁厚度、瓣膜功能、心脏收缩和舒张功能等。', '', '', '《超声心动图学》', '心脏检查,超声,无创', 'manual', 'published', 1, 1),
('胃镜', 3, '胃镜是通过口腔或鼻腔插入内镜观察食管、胃和十二指肠的检查方法。', '胃镜是一种带有微型摄像头的柔性内镜，可直接观察上消化道黏膜病变。', '', '', '用于诊断胃炎、胃溃疡、十二指肠溃疡、食管癌、胃癌等。', '', '', '《消化内镜学》', '消化检查,内镜,微创', 'manual', 'published', 1, 1),
('MRI', 3, '磁共振成像是利用磁场和无线电波对人体进行断层成像的检查方法。', 'MRI是通过磁场和射频脉冲使人体组织中的氢原子核共振，产生信号并重建图像。', '', '', '用于诊断中枢神经系统疾病、骨关节疾病、腹部脏器疾病等。', '', '', '《医学影像学》', '影像学,磁共振,无创', 'manual', 'published', 1, 1),
('血常规', 4, '血常规是通过检测血液中红细胞、白细胞、血小板等指标评估全身健康状况的基础检查。', '血常规是对血液中各种血细胞数量和形态的检测。', '', '', '用于判断贫血、感染、出血倾向等。', '', '', '《临床检验基础》', '血液检查,基础检验,常规', 'manual', 'published', 1, 1),
('血糖检测', 4, '血糖检测是测量血液中葡萄糖浓度的检查，用于诊断和监测糖尿病。', '血糖检测是通过化学或酶学方法测定血液中葡萄糖的含量。', '', '', '用于诊断糖尿病、评估血糖控制情况。', '', '', '《临床生物化学检验》', '生化检查,糖尿病,血糖', 'manual', 'published', 1, 1),
('肝功能检查', 4, '肝功能检查是通过检测血清中转氨酶、胆红素、白蛋白等指标评估肝脏功能的检查。', '肝功能检查是对肝脏代谢、合成、解毒等功能的综合评估。', '', '', '用于诊断肝炎、肝硬化、肝功能损伤等。', '', '', '《临床生物化学检验》', '生化检查,肝脏,酶学', 'manual', 'published', 1, 1),
('肾功能检查', 4, '肾功能检查是通过检测血清肌酐、尿素氮、尿酸等指标评估肾脏功能的检查。', '肾功能检查是对肾脏滤过、排泄等功能的评估。', '', '', '用于诊断肾功能不全、肾炎、肾结石等。', '', '', '《临床生物化学检验》', '生化检查,肾脏,滤过', 'manual', 'published', 1, 1),
('凝血功能检查', 4, '凝血功能检查是评估血液凝固能力的检查，用于诊断出血或血栓性疾病。', '凝血功能检查是对血液凝固过程中各项指标的检测。', '', '', '用于诊断凝血障碍、评估手术风险。', '', '', '《临床检验基础》', '血液检查,凝血,血栓', 'manual', 'published', 1, 1),
('阑尾切除术', 5, '阑尾切除术是治疗急性阑尾炎的标准手术，通过切除发炎的阑尾消除感染。', '阑尾切除术是将发炎或感染的阑尾切除的外科手术。', '', '', '', '用于治疗急性阑尾炎、慢性阑尾炎急性发作。', '', '《外科学》', '普外科,急诊手术,阑尾', 'manual', 'published', 1, 1),
('胆囊切除术', 5, '胆囊切除术是治疗胆囊结石、胆囊炎等疾病的常用手术。', '胆囊切除术是将胆囊切除的外科手术，可采用开腹或腹腔镜方式。', '', '', '', '用于治疗胆囊结石、慢性胆囊炎、胆囊息肉等。', '', '《外科学》', '普外科,腹腔镜,胆囊', 'manual', 'published', 1, 1),
('剖宫产术', 5, '剖宫产术是通过腹部切口将胎儿娩出的分娩方式。', '剖宫产术是在无法经阴道分娩或存在分娩风险时，通过手术方式娩出胎儿。', '', '', '', '用于胎位异常、胎儿窘迫、产程停滞、多胎妊娠等情况。', '', '《妇产科学》', '妇产科,分娩,手术', 'manual', 'published', 1, 1),
('骨折复位固定术', 5, '骨折复位固定术是将骨折断端恢复正常位置并固定的手术。', '骨折复位固定术是通过手术将骨折断端准确复位，并使用钢板、螺钉、髓内钉等固定。', '', '', '', '用于治疗各种骨折，恢复骨骼的连续性和功能。', '', '《骨科学》', '骨科,骨折,固定', 'manual', 'published', 1, 1),
('冠状动脉搭桥术', 5, '冠状动脉搭桥术是通过移植血管为狭窄的冠状动脉建立旁路的手术。', '冠状动脉搭桥术是将患者自身的血管移植到冠状动脉狭窄部位的远端，以改善心肌供血。', '', '', '', '用于治疗严重冠心病，改善心肌缺血。', '', '《心脏外科学》', '心血管外科,冠心病,搭桥', 'manual', 'published', 1, 1),
('全身麻醉', 6, '全身麻醉是通过药物使患者意识消失、全身无痛的麻醉方式。', '全身麻醉是通过吸入或静脉注射麻醉药物，使患者进入无意识、无疼痛状态。', '', '', '', '用于各类手术，尤其是大型手术或患者无法配合的手术。', '', '《麻醉学》', '麻醉,全麻,手术', 'manual', 'published', 1, 1),
('椎管内麻醉', 6, '椎管内麻醉是将麻醉药物注入椎管内，使下半身无痛的麻醉方式。', '椎管内麻醉包括硬膜外麻醉和蛛网膜下腔麻醉，通过阻滞脊神经传导实现麻醉。', '', '', '', '用于下腹部、盆腔、下肢手术。', '', '《麻醉学》', '麻醉,椎管内,半身', 'manual', 'published', 1, 1),
('局部麻醉', 6, '局部麻醉是将麻醉药物注射到手术部位周围，使局部区域无痛的麻醉方式。', '局部麻醉通过阻滞局部神经末梢的传导，使特定区域失去痛觉。', '', '', '', '用于小型手术、局部操作、疼痛治疗。', '', '《麻醉学》', '麻醉,局麻,局部', 'manual', 'published', 1, 1),
('神经阻滞麻醉', 6, '神经阻滞麻醉是将麻醉药物注射到神经干周围，阻滞神经传导的麻醉方式。', '神经阻滞麻醉通过在神经干周围注射麻醉药物，使该神经支配区域产生麻醉效果。', '', '', '', '用于四肢手术、疼痛治疗。', '', '《麻醉学》', '麻醉,神经阻滞,区域', 'manual', 'published', 1, 1),
('镇静麻醉', 6, '镇静麻醉是通过药物使患者处于镇静状态，但保持自主呼吸和基本生理反射。', '镇静麻醉通过静脉注射镇静药物，使患者进入意识模糊但可唤醒的状态。', '', '', '', '用于内镜检查、介入治疗等。', '', '《麻醉学》', '麻醉,镇静,内镜', 'manual', 'published', 1, 1),
('合理膳食', 7, '合理膳食是指摄入多样化、均衡的食物，满足身体营养需求。', '合理膳食是根据年龄、性别、身体活动水平等因素，制定科学的饮食方案。', '', '', '', '', '主食粗细搭配、多吃蔬菜水果、适量摄入优质蛋白、减少高油高盐高糖食物。', '《中国居民膳食指南》', '营养,饮食,健康', 'manual', 'published', 1, 1),
('规律运动', 7, '规律运动是指每周进行适度的体育锻炼，增强体质和健康水平。', '规律运动是按照一定频率和强度进行的身体活动。', '', '', '', '', '每周至少150分钟中等强度有氧运动，如快走、慢跑、游泳等；结合力量训练。', '《中国成人身体活动指南》', '运动,锻炼,健康', 'manual', 'published', 1, 1),
('戒烟限酒', 7, '戒烟限酒是维护健康的重要措施，可降低多种疾病风险。', '戒烟限酒是指戒除吸烟习惯，限制饮酒量。', '', '', '', '', '吸烟有害健康，应彻底戒除；男性每日饮酒量不超过25g酒精，女性不超过15g。', '《中国居民健康素养66条》', '戒烟,限酒,健康', 'manual', 'published', 1, 1),
('心理健康', 7, '心理健康是指心理状态良好，能够应对压力和情绪变化。', '心理健康是指个体心理活动正常，情绪稳定，人际关系和谐。', '', '', '', '', '保持积极心态、学会情绪管理、建立良好人际关系、必要时寻求心理支持。', '《心理健康教育指南》', '心理,情绪,健康', 'manual', 'published', 1, 1),
('定期体检', 7, '定期体检是通过系统性检查，早期发现健康问题，预防疾病发生。', '定期体检是按照一定周期进行的全面健康检查。', '', '', '', '', '每年进行一次全面体检，包括血常规、生化、影像学等检查。', '《健康体检基本项目专家共识》', '体检,预防,健康', 'manual', 'published', 1, 1);
