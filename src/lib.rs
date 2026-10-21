use pumpkin_plugin_api::{
    Context, Plugin, PluginMetadata, Server,
    command::{Command, CommandError, CommandSender, ConsumedArgs},
    commands::CommandHandler,
    permission::{Permission, PermissionDefault},
    permissions::FS_READ_DATA,
    text::TextComponent,
};
use serde_json::{Value, json};
use std::sync::OnceLock;

static DATA_FOLDER: OnceLock<String> = OnceLock::new();
static SERVER_VERSION: OnceLock<String> = OnceLock::new();
const FIXES: [u64; 26] = [
    3844, 3759, 4048, 3516, 4089, 3972, 4123, 3847, 3918, 3933, 3969, 4063, 4090,
    3989, 3065, 3716, 3698, 3730, 2016, 4045, 3902, 3571, 3510, 3367, 3511, 3512,
];

// Same brackets, bold initials and warm palette as ArkPerm's [AP] prefix.
fn prefix() -> Vec<Value> {
    vec![
        json!({"text":"[","color":"#D7B899"}),
        json!({"text":"A","color":"#FFB347","bold":true}),
        json!({"text":"B","color":"#E36A2E","bold":true}),
        json!({"text":"] ","color":"#D7B899"}),
    ]
}

fn message(parts: Vec<Value>) -> TextComponent {
    let mut extra = prefix();
    extra.extend(parts);
    TextComponent::from_json(&json!({"text":"","extra":extra}).to_string())
        .unwrap_or_else(|_| TextComponent::text("[AB]"))
}

fn status(version: &str) -> Option<Vec<u64>> {
    let path = format!("{}/status.json", DATA_FOLDER.get()?);
    let report: Value = serde_json::from_str(&std::fs::read_to_string(path).ok()?).ok()?;
    // A cached report for another engine must never activate or display a fix.
    if report["server_version"].as_str()? != version {
        return None;
    }
    let applied = report["applied_fixes"].as_array()?;
    Some(
        FIXES
            .into_iter()
            .filter(|id| applied.iter().any(|v| v.as_u64() == Some(*id)))
            .collect(),
    )
}

struct Status;
impl CommandHandler for Status {
    fn handle(
        &self,
        sender: CommandSender,
        _server: Server,
        _args: ConsumedArgs,
    ) -> Result<i32, CommandError> {
        // A process cannot change its engine version; avoid a full host system
        // scan on each command just to read this immutable string.
        let version = SERVER_VERSION
            .get()
            .map(String::as_str)
            .unwrap_or("inconnue");
        sender.send_message(message(vec![json!({
            "text":format!("Version du serveur : Pumpkin {version}"),"color":"#E6A15A"
        })]));
        let mut parts = vec![json!({"text":"Correctifs appliqués : ","color":"#D7B899"})];
        match status(version) {
            Some(ids) if !ids.is_empty() => {
                for (index, id) in ids.iter().enumerate() {
                    if index != 0 {
                        parts.push(json!({"text":", ","color":"#D7B899"}));
                    }
                    parts.push(json!({
                        "text":format!("#{id}"),"color":"#FFD166",
                        "click_event":{"action":"open_url","url":format!("https://github.com/Pumpkin-MC/Pumpkin/issues/{id}")}
                    }));
                }
            }
            Some(_) => parts.push(json!({"text":"aucun.","color":"#D7B899"})),
            None => parts.push(json!({"text":"vérification indisponible.","color":"#D7B899"})),
        }
        sender.send_message(message(parts));
        Ok(1)
    }
}

struct ArkBug;
impl Plugin for ArkBug {
    fn new() -> Self {
        Self
    }
    fn metadata(&self) -> PluginMetadata {
        PluginMetadata {
            name: "ArkBug".into(),
            version: env!("CARGO_PKG_VERSION").into(),
            authors: vec![env!("CARGO_PKG_AUTHORS").into()],
            description: "Correctifs Pumpkin sélectionnés selon la version du serveur.".into(),
            dependencies: vec![],
            permissions: vec![FS_READ_DATA.into()],
        }
    }
    fn on_load(&self, context: Context) -> pumpkin_plugin_api::Result<()> {
        let _ = SERVER_VERSION.set(context.get_server().get_sys_info().pumpkin_version);
        let _ = DATA_FOLDER.set(context.get_data_folder());
        context.register_permission(&Permission {
            node: "ArkBug:arkbug.status".into(),
            description: "Consulter les correctifs ArkBug".into(),
            default: PermissionDefault::Allow,
            children: vec![],
        })?;
        context.register_command(
            Command::new(&["arkbug".into()], "État des correctifs ArkBug").execute(Status),
            "arkbug.status",
        );
        Ok(())
    }
}
pumpkin_plugin_api::register_plugin!(ArkBug);
