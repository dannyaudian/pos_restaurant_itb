import frappe
import click
from frappe.commands import pass_context

@click.command('sync-kitchen-display')
@click.option('--verbose', is_flag=True, default=False, help='Verbose output')
@pass_context
def sync_kitchen_display(context, verbose=False):
    """
    Sync Kitchen Order Tickets (KOTs) with status 'New' to Kitchen Display Orders.
    
    This command finds all KOTs with status 'New' and creates corresponding 
    Kitchen Display Orders using the create_kds_from_kot API method.
    """
    site = context.sites[0]
    
    with frappe.init_site(site):
        frappe.connect()
        try:
            # Get all KOTs with status "New"
            click.secho(f"Finding KOTs with status 'New'...", fg="blue")
            new_kots = frappe.get_all(
                "KOT", 
                filters={"status": "New"}, 
                fields=["name", "creation", "owner"]
            )
            
            if not new_kots:
                click.secho("No new KOTs found for syncing.", fg="yellow")
                return
                
            click.secho(f"Found {len(new_kots)} KOTs to process.", fg="green")
            
            # Import the create_kds_from_kot function
            from pos_restaurant_itb.api.kds_handler import create_kds_from_kot
            
            # Process each KOT
            success_count = 0
            error_count = 0
            
            for kot in new_kots:
                try:
                    if verbose:
                        click.secho(f"Processing KOT: {kot.name}", fg="blue")
                    
                    # Call the API method to create Kitchen Display Order
                    result = create_kds_from_kot(kot.name)
                    
                    if result.get("status") == "success":
                        success_count += 1
                        if verbose or result.get("status") != "warning":
                            click.secho(f"✓ {result.get('message')}", fg="green")
                    elif result.get("status") == "warning":
                        # KDS already exists - not an error but not a new creation
                        success_count += 1
                        if verbose:
                            click.secho(f"⚠ {result.get('message')}", fg="yellow")
                    else:
                        error_count += 1
                        click.secho(f"✗ Failed to sync KOT {kot.name}: {result.get('message')}", fg="red")
                        
                except Exception as e:
                    error_count += 1
                    click.secho(f"✗ Error processing KOT {kot.name}: {str(e)}", fg="red")
                    # Log the error but continue processing other KOTs
                    frappe.log_error(
                        message=f"Error syncing KOT {kot.name} to Kitchen Display: {str(e)}",
                        title="KOT Sync Error"
                    )
            
            # Final summary
            click.secho(
                f"Sync completed: {success_count} successful, {error_count} failed.",
                fg="blue" if error_count == 0 else "yellow"
            )
            
            # If all operations were successful, display a success message
            if error_count == 0 and success_count > 0:
                click.secho(
                    f"All KOTs were successfully synced to Kitchen Display Orders.",
                    fg="green"
                )
                
        except Exception as e:
            click.secho(f"Error: {str(e)}", fg="red")
            frappe.log_error(
                message=f"Error in sync_kitchen_display command: {str(e)}",
                title="KOT Sync Command Error"
            )
        finally:
            frappe.destroy()

commands = [
    sync_kitchen_display
]