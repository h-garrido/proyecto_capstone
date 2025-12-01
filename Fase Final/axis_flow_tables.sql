CREATE DATABASE IF NOT EXISTS axis_bd
CHARACTER SET utf8mb4 
COLLATE utf8mb4_unicode_ci;

USE axis_bd;

-- ============================================================
-- 1. TABLA: operario
-- ============================================================
DROP TABLE IF EXISTS ejecucion_operario;
DROP TABLE IF EXISTS ejecucion_proceso;
DROP TABLE IF EXISTS proceso;
DROP TABLE IF EXISTS bano;
DROP TABLE IF EXISTS operario;

CREATE TABLE operario (
    id_op INT AUTO_INCREMENT PRIMARY KEY,
    nom_op VARCHAR(50) NOT NULL,
    ap_pa_op VARCHAR(50),
    ap_ma_op VARCHAR(50),
    sigla_op VARCHAR(3),
    UNIQUE KEY ux_operario_sigla (sigla_op)
);


-- ============================================================
-- 2. TABLA: bano
-- ============================================================

CREATE TABLE bano (
    id_b INT PRIMARY KEY,
    variante ENUM(
        'B1',
        'B1E',
        'B2',
        'B2E',
        'B2b',
        'B3',
        'B3E',
        'B4',
        'B4E',
        'B4b',
        'B5',
        'B6',
        'B6E'
    ) NOT NULL,

    edificio ENUM('A', 'B', 'C') NOT NULL,
    piso SMALLINT NOT NULL,

    UNIQUE KEY ux_bano_ident (id_b, edificio, piso, variante)
);


-- ============================================================
-- 3. TABLA: proceso
-- ============================================================

CREATE TABLE proceso (
    id_proc INT AUTO_INCREMENT PRIMARY KEY,
    nom_proc VARCHAR(100) NOT NULL,
    tt_proc INT NOT NULL
);


-- ============================================================
-- 4. TABLA DE HECHOS: ejecucion_proceso
-- ============================================================

CREATE TABLE ejecucion_proceso (
    id_ejec INT AUTO_INCREMENT PRIMARY KEY,

    id_b INT NOT NULL,
    id_proc INT NOT NULL,
    fecha DATE NOT NULL,

    edificio ENUM('A', 'B', 'C') NOT NULL,
    piso SMALLINT NOT NULL,

    tipo_bano VARCHAR(50) GENERATED ALWAYS AS (
    CONCAT(id_b, '-', edificio, '-', piso, '-', variante)
	) STORED,

    variante ENUM(
        'B1',
        'B1E',
        'B2',
        'B2E',
        'B2b',
        'B3',
        'B3E',
        'B4',
        'B4E',
        'B4b',
        'B5',
        'B6',
        'B6E'
    ) NOT NULL,

    tt_proc INT NOT NULL,
    t_real_min DECIMAL(10,2) NOT NULL,
    t_espera_min DECIMAL(10,2) DEFAULT 0,
    t_real_acum_min DECIMAL(12,2) DEFAULT NULL,

    diferencia_tt_min DECIMAL(10,2) GENERATED ALWAYS AS (t_real_min - tt_proc) STORED,
    cumple_tt TINYINT(1) GENERATED ALWAYS AS (t_real_min <= tt_proc) STORED,
    porcentaje_tt DECIMAL(5,2) GENERATED ALWAYS AS ((t_real_min / NULLIF(tt_proc,0)) * 100) STORED,

    t_real_horas DECIMAL(10,4) GENERATED ALWAYS AS (t_real_min / 60) STORED,
    t_espera_horas DECIMAL(10,4) GENERATED ALWAYS AS (t_espera_min / 60) STORED,
    t_real_acum_horas DECIMAL(12,4) GENERATED ALWAYS AS (t_real_acum_min / 60) STORED,

    -- FK
    CONSTRAINT fk_ejec_bano FOREIGN KEY (id_b) REFERENCES bano(id_b),
    CONSTRAINT fk_ejec_proc FOREIGN KEY (id_proc) REFERENCES proceso(id_proc),

    INDEX idx_ejec_fecha (fecha),
    INDEX idx_ejec_proc (id_proc),
    INDEX idx_ejec_bano_fecha (id_b, fecha)
);


-- ============================================================
-- 5. TABLA PUENTE: ejecucion_operario (N:M)
-- ============================================================

CREATE TABLE ejecucion_operario (
    id_ejec_op INT AUTO_INCREMENT PRIMARY KEY,
    id_ejec INT NOT NULL,
    id_op INT NOT NULL,

    rol ENUM('Operario_1','Operario_2','Operario_3') DEFAULT 'Operario_1',

    CONSTRAINT fk_ejec_op_ejec FOREIGN KEY (id_ejec)
        REFERENCES ejecucion_proceso(id_ejec)
        ON DELETE CASCADE,

    CONSTRAINT fk_ejec_op_op FOREIGN KEY (id_op)
        REFERENCES operario(id_op)
        ON DELETE RESTRICT,

    UNIQUE KEY ux_ejec_op (id_ejec, id_op)
);
