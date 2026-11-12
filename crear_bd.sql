-- ============================================================
-- Biblioteca Digital de Instrucciones - Impresos Múltiples
-- Tarea 3: base de datos MySQL (importar en phpMyAdmin)
-- Crea la base, sus tablas y datos de ejemplo.
-- ATENCIÓN: borra las tablas si ya existen y las vuelve a crear.
-- No contiene archivos reales: los documentos se suben desde el sistema.
-- ============================================================

-- Los textos llevan acentos: se indica que el script viene en UTF-8
SET NAMES utf8mb4;

CREATE DATABASE IF NOT EXISTS biblioteca_instrucciones
  CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE biblioteca_instrucciones;

DROP TABLE IF EXISTS documentos;
DROP TABLE IF EXISTS historial_versiones;
DROP TABLE IF EXISTS instrucciones;

-- Tabla padre: una fila por instrucción de trabajo
CREATE TABLE instrucciones (
  id INT AUTO_INCREMENT PRIMARY KEY,
  titulo VARCHAR(150) NOT NULL,
  proceso VARCHAR(80) NOT NULL,
  version INT NOT NULL DEFAULT 1,
  fecha_actualizacion DATE NOT NULL,
  estado ENUM('activa', 'archivada') NOT NULL DEFAULT 'activa'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Historial de versiones de la instrucción (viene del Desafío 2)
CREATE TABLE historial_versiones (
  id INT AUTO_INCREMENT PRIMARY KEY,
  instruccion_id INT NOT NULL,
  version INT NOT NULL,
  fecha DATE NOT NULL,
  CONSTRAINT fk_historial_instruccion FOREIGN KEY (instruccion_id)
    REFERENCES instrucciones (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Tabla de archivos (Tarea 3): cada fila es una versión del documento de una instrucción.
-- El contenido del archivo se guarda en la columna LONGBLOB.
-- ON DELETE CASCADE: al eliminar la instrucción se eliminan todas sus versiones.
CREATE TABLE documentos (
  id INT AUTO_INCREMENT PRIMARY KEY,
  instruccion_id INT NOT NULL,
  version INT NOT NULL,
  nombre_original VARCHAR(255) NOT NULL,
  tipo_mime VARCHAR(100) NOT NULL,
  tamano INT NOT NULL,
  contenido LONGBLOB NOT NULL,
  enlace_video VARCHAR(500) NULL,
  fecha_subida DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uq_documento_version (instruccion_id, version),
  CONSTRAINT fk_documento_instruccion FOREIGN KEY (instruccion_id)
    REFERENCES instrucciones (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Datos de ejemplo (8 instrucciones). Los documentos se suben desde el sistema.
INSERT INTO instrucciones (titulo, proceso, version, fecha_actualizacion) VALUES
  ('Empaque de producto terminado', 'Empaque', 3, CURDATE() - INTERVAL 20 DAY),
  ('Ajuste de máquina troqueladora', 'Troquelado', 2, CURDATE() - INTERVAL 160 DAY),
  ('Cambio de tinta en impresora offset', 'Impresión', 4, CURDATE() - INTERVAL 45 DAY),
  ('Control de calidad de etiquetas', 'Calidad', 1, CURDATE() - INTERVAL 230 DAY),
  ('Corte de papel en guillotina', 'Corte', 3, CURDATE() - INTERVAL 90 DAY),
  ('Limpieza de planchas flexográficas', 'Impresión', 2, CURDATE() - INTERVAL 300 DAY),
  ('Pegado de cajas plegadizas', 'Empaque', 1, CURDATE() - INTERVAL 170 DAY),
  ('Aplicación de mangas termoencogibles', 'Etiquetado', 2, CURDATE() - INTERVAL 5 DAY);

INSERT INTO historial_versiones (instruccion_id, version, fecha) VALUES
  (1, 1, CURDATE() - INTERVAL 140 DAY), (1, 2, CURDATE() - INTERVAL 80 DAY), (1, 3, CURDATE() - INTERVAL 20 DAY),
  (2, 1, CURDATE() - INTERVAL 220 DAY), (2, 2, CURDATE() - INTERVAL 160 DAY),
  (3, 1, CURDATE() - INTERVAL 225 DAY), (3, 2, CURDATE() - INTERVAL 165 DAY), (3, 3, CURDATE() - INTERVAL 105 DAY), (3, 4, CURDATE() - INTERVAL 45 DAY),
  (4, 1, CURDATE() - INTERVAL 230 DAY),
  (5, 1, CURDATE() - INTERVAL 210 DAY), (5, 2, CURDATE() - INTERVAL 150 DAY), (5, 3, CURDATE() - INTERVAL 90 DAY),
  (6, 1, CURDATE() - INTERVAL 360 DAY), (6, 2, CURDATE() - INTERVAL 300 DAY),
  (7, 1, CURDATE() - INTERVAL 170 DAY),
  (8, 1, CURDATE() - INTERVAL 65 DAY), (8, 2, CURDATE() - INTERVAL 5 DAY);
